import logging
import re
from collections import Counter
from collections.abc import Callable
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from uniinfo_editor import UniInfoTUI

from uniinfo_editor import register_plugin

logger = logging.getLogger('uniinfo')

# 汉字范围（不额外依赖 regex 包）
HAN = re.compile(r'[一-鿿]')

# 连续三同字：滴滴滴 / 哈哈哈
REPEATED_CHAR = re.compile(r'(.)\1{2,}')

# 拉丁 / 假名 / 谚文：用于把「デジタルハリウッド大学」这类外文校名排除出「过短」
NON_HAN_SCRIPT = re.compile(r'[A-Za-z぀-ヿ가-힯]')

# 基础教育阶段写法，取自 generator/province.py 的 NORMAL_NAME_MATCHER 反向
SCHOOL_LEVEL = re.compile(
    r'中学(?!院)|中學|高中|初中|小学|小學|附中|职高|职专|中专|中技|技校|职中|民中'
    r'|职校|职教中心|职业教育中心'
    r'|[一二三四五六七八九十\d]+(?:中|高|职)(?:学|校|部|新区)?$'
)


def _school_rows(tui: UniInfoTUI) -> list[tuple[str, str]] | None:
    """逐行取出 (答题ID, 学校名)；数据未就绪时返回 None（已自行报错）"""
    if tui.df is None:
        logger.error('❌ 内存中未发现任何数据，请先执行 `load`。')
        return None

    school_col = tui.get_school_column()
    if school_col is None:
        logger.error(f'❌ 在 {tui.mode} 模式下未定位到学校名称列。')
        return None

    row_to_id = {row: id_ for id_, row in (tui.id_to_row_index() or {}).items()}
    return [
        (row_to_id.get(i, '-'), ' '.join(str(name).split()))
        for i, name in enumerate(tui.df[school_col].to_list())
        if name is not None
    ]


def _joke_rule(name: str) -> str | None:
    """恶作剧 / 无效填答的结构特征

    外文校名与基础教育学段各自另有归属，这里不重复报。
    """
    if not HAN.search(name) or SCHOOL_LEVEL.search(name):
        return None
    if REPEATED_CHAR.search(name):
        return '叠字'

    han_count = len(HAN.findall(name))
    if han_count > 20:
        return '超长(混入备注)'
    if han_count < 3 and not NON_HAN_SCRIPT.search(name):
        return '过短'
    return None


def _level_rule(name: str) -> str | None:
    return '基础教育' if SCHOOL_LEVEL.search(name) else None


def _scan(
    rows: list[tuple[str, str]], rule_of: Callable[[str], str | None]
) -> tuple[Counter[str], dict[str, str], dict[str, list[str]]]:
    counts: Counter[str] = Counter()
    rules: dict[str, str] = {}
    ids: dict[str, list[str]] = {}
    for id_, name in rows:
        rule = rule_of(name)
        if rule is None:
            continue
        counts[name] += 1
        rules.setdefault(name, rule)
        ids.setdefault(name, []).append(id_)
    return counts, rules, ids


def _render(
    title: str,
    counts: Counter[str],
    rules: dict[str, str],
    ids: dict[str, list[str]],
    limit: int,
    verbose: bool,
) -> None:
    ordered = sorted(counts, key=lambda n: (-counts[n], n))
    shown = ordered if limit == 0 else ordered[:limit]

    table = Table(title=title, show_header=True, box=None)
    table.add_column(
        '学校名', style='bold', max_width=40, overflow='ellipsis', no_wrap=True
    )
    table.add_column('次数', justify='right')
    table.add_column('规则')
    table.add_column('样例 ID', style='dim')
    for name in shown:
        sample = ids[name] if verbose else ids[name][:3]
        table.add_row(name, str(counts[name]), rules[name], ' '.join(sample))
    Console().print(table)

    if len(shown) < len(ordered):
        logger.info(f'仅显示前 {len(shown)} / {len(ordered)} 个，--limit 0 查看全部')


# =====================================================================
# ⚙️ 用 Click 构建多级子命令组
# =====================================================================
@click.group(name='check')
def check_group() -> None:
    """大学数据多维度异常校验 (joke/school/merge/typo)"""
    pass


@check_group.command(name='joke')
@click.option(
    '--limit',
    type=int,
    default=20,
    metavar='N',
    help='展示条数上限 (默认 20，0 为不限)',
)
@click.option('--verbose', is_flag=True, help='列出命中的全部答题 ID')
@click.pass_obj
def check_joke(tui: UniInfoTUI, limit: int, verbose: bool) -> None:
    """扫描恶作剧大学名称"""
    rows = _school_rows(tui)
    if rows is None:
        return

    counts, rules, ids = _scan(rows, _joke_rule)
    if not counts:
        logger.info(f'🎉 未发现异常 ({tui.mode}，样本 {len(rows)} 条)')
        return

    logger.info(
        f'🔍 命中 {sum(counts.values())} 条 / {len(counts)} 个校名 ({tui.mode}，样本 {len(rows)} 条)'
    )
    _render('🎭 疑似恶作剧 / 无效填答', counts, rules, ids, limit, verbose)


@check_group.command(name='school')
@click.option(
    '--limit',
    type=int,
    default=20,
    metavar='N',
    help='展示条数上限 (默认 20，0 为不限)',
)
@click.option('--verbose', is_flag=True, help='列出命中的全部答题 ID')
@click.pass_obj
def check_school(tui: UniInfoTUI, limit: int, verbose: bool) -> None:
    """筛查误填的中学、小学名称"""
    rows = _school_rows(tui)
    if rows is None:
        return

    counts, rules, ids = _scan(rows, _level_rule)
    if not counts:
        logger.info(f'🎉 未发现异常 ({tui.mode}，样本 {len(rows)} 条)')
        return

    logger.info(
        f'🔍 命中 {sum(counts.values())} 条 / {len(counts)} 个校名 ({tui.mode}，样本 {len(rows)} 条)'
    )
    _render('🏫 疑似误填的中学 / 小学', counts, rules, ids, limit, verbose)


@check_group.command(name='merge')
@click.pass_obj
def check_merge(tui: UniInfoTUI) -> None:
    """分析数据中可合并的潜在相似大学名称"""
    rows = _school_rows(tui)
    if rows is None:
        return
    logger.info(f'🔍 正在分析可合并的大学名称... ({tui.mode}，样本 {len(rows)} 条)')


@check_group.command(name='typo')
@click.option(
    '--threshold', type=float, default=0.8, help='相似度阈值 (默认 0.8)'
)
@click.pass_obj
def check_typo(tui: UniInfoTUI, threshold: float) -> None:
    """基于阈值距离筛查名称错别字"""
    rows = _school_rows(tui)
    if rows is None:
        return
    logger.info(
        f'🔍 正在以相似度 {threshold} 筛查错别字名称... ({tui.mode}，样本 {len(rows)} 条)'
    )


# 注册该 Click 顶层命令组到主框架路由中
register_plugin(check_group)

run_check = check_group
