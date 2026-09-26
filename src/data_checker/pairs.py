import re
from collections import Counter
from collections.abc import Iterable, Iterator
from functools import lru_cache

from pypinyin import lazy_pinyin
from hanzi_chaizi import HanziChaizi

from data_checker.normalize import PLACE, TIER, core_name, norm

_CHAIZI = HanziChaizi()


@lru_cache(maxsize=None)
def pinyin_of(name: str) -> tuple[str, ...]:
    return tuple(lazy_pinyin(name))


@lru_cache(maxsize=None)
def parts_of(char: str) -> frozenset[str]:
    """字的部件（含字本身）；查不到时退化为只有字本身"""
    return frozenset([char] + (_CHAIZI.query(char) or []))


def char_doc_freq(counts: Counter[str]) -> Counter[str]:
    """每个字出现在多少个不同校名里：用来判定「罕见字」"""
    freq: Counter[str] = Counter()
    for name in counts:
        freq.update(set(norm(name)))
    return freq


def prefix_len(a: str, b: str) -> int:
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    return i


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _buckets(names: Iterable[str], key_of) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {}
    for name in names:
        buckets.setdefault(key_of(name), []).append(name)
    return buckets


def _ranked(groups: list[list[str]], counts: Counter[str]) -> list[tuple[str, list[str]]]:
    """每组选出建议写法（频次最高、其次最短），全组按总频次排序"""
    out = [
        (
            max(m, key=lambda n: (counts[n], -len(n))),
            sorted(m, key=lambda n: (-counts[n], n)),
        )
        for m in groups
    ]
    out.sort(key=lambda kv: -sum(counts[n] for n in kv[1]))
    return out


def merge_groups(counts: Counter[str]) -> list[tuple[str, list[str]]]:
    """归一化后同组的写法：校区、括号、繁简、空白等异写"""
    buckets = _buckets(counts, norm)
    return _ranked([m for m in buckets.values() if len(m) > 1], counts)


def pending_groups(counts: Counter[str]) -> list[tuple[str, list[str]]]:
    """core 相同但归一化不同：可能是同一所学校（如 XX大学 / XX学院），只提示不自动合"""
    buckets: dict[str, list[str]] = {}
    for name in counts:
        key = core_name(name)
        if len(key) >= 2:
            buckets.setdefault(key, []).append(name)
    return _ranked(
        [
            m
            for m in buckets.values()
            if len(m) > 1 and len({norm(n) for n in m}) > 1
        ],
        counts,
    )


def candidate_pairs(names: Iterable[str]) -> Iterator[tuple[str, str]]:
    """按归一化后的首 4 字 / 末 4 字分桶，避免全两两比较"""
    buckets: dict[str, list[str]] = {}
    for name in names:
        key = norm(name)
        for b in (key[:4], key[-4:]):
            buckets.setdefault(b, []).append(name)

    seen: set[tuple[str, str]] = set()
    for bucket in buckets.values():
        if len(bucket) > 2000:
            continue
        for i in range(len(bucket)):
            for j in range(i + 1, len(bucket)):
                pair = (bucket[i], bucket[j])
                if pair not in seen:
                    seen.add(pair)
                    yield pair


def typo_pairs(
    counts: Counter[str], max_diff: int, min_hi: int, rare_df: int = 1
) -> list[tuple[str, str, str]]:
    """(疑似错字, 建议写法, 类型)

    类型：同音（拼音序列相同，字形不同）/ 形近（换成罕见字）
    / 尾部差异（字形大部分相同，只有尾部小差异）

    rare_df：字出现在不超过 rare_df 个校名里就算罕见字
    """
    out = []
    # 同一学校可能有多种写法，比较热度要用「归一化后整组」的频次
    group: Counter[str] = Counter()
    for name, c in counts.items():
        group[norm(name)] += c
    rare = char_doc_freq(counts)

    for a, b in candidate_pairs(counts):
        na, nb = norm(a), norm(b)
        if na == nb:
            continue

        if group[na] <= group[nb]:
            lo, hi, lo_s, hi_s = a, b, na, nb
        else:
            lo, hi, lo_s, hi_s = b, a, nb, na
        if group[lo_s] > 2 or group[hi_s] < min_hi:
            continue

        # 等长且整串同音：山西/陕西、福州/抚州 这类地名与虚词错误
        if len(na) == len(nb) and pinyin_of(na) == pinyin_of(nb):
            out.append((lo, hi, '同音'))
            continue

        # 单字替换，且低频侧用到罕见字、高频侧是常用字：囗/口 这类形近错字
        if len(na) == len(nb):
            diff = [i for i in range(len(na)) if na[i] != nb[i]]
            if len(diff) == 1:
                i = diff[0]
                x, y = lo_s[i], hi_s[i]
                if rare[x] <= rare_df < rare[y] and parts_of(x) & parts_of(y):
                    out.append((lo, hi, '形近'))
                    continue

        if na in nb or nb in na:
            lo_n, hi_n = (na, nb) if len(na) <= len(nb) else (nb, na)
            # 多出来的部分若只是尾部的重复（「XX大学大学」）→ 冗余，仍算错字
            if not lo_n.endswith(hi_n[len(lo_n) :]):
                continue
        if abs(len(na) - len(nb)) > 1:
            continue

        cp = prefix_len(na, nb)
        if cp < 4 or cp < 0.6 * min(len(na), len(nb)):
            continue
        tail = na[cp:] + nb[cp:]
        if PLACE.search(tail) or TIER.search(tail):
            continue
        if edit_distance(na[cp:], nb[cp:]) > max_diff:
            continue
        out.append((lo, hi, '尾部差异'))
    out.sort(key=lambda p: (-counts[p[1]], -counts[p[0]]))
    return out
