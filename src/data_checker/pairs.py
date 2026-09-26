from collections import Counter
from collections.abc import Iterable

from data_checker.normalize import core_name, norm


def _buckets(names: Iterable[str], key_of) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {}
    for name in names:
        buckets.setdefault(key_of(name), []).append(name)
    return buckets


def _ranked(
    groups: list[list[str]], counts: Counter[str]
) -> list[tuple[str, list[str]]]:
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
        [m for m in buckets.values() if len(m) > 1 and len({norm(n) for n in m}) > 1],
        counts,
    )
