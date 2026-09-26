import logging
from collections import Counter
from collections.abc import Callable
from typing import TYPE_CHECKING

import click
from uniinfo_editor import register_plugin

from data_checker.render import render
from data_checker.rules import joke_rule, level_rule

if TYPE_CHECKING:
    from uniinfo_editor import UniInfoTUI

logger = logging.getLogger('uniinfo')


def school_rows(tui: UniInfoTUI) -> list[tuple[str, str]] | None:
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


def scan(
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
    rows = school_rows(tui)
    if rows is None:
        return

    counts, rules, ids = scan(rows, joke_rule)
    if not counts:
        logger.info(f'🎉 未发现异常 ({tui.mode}，样本 {len(rows)} 条)')
        return

    logger.info(
        f'🔍 命中 {sum(counts.values())} 条 / {len(counts)} 个校名 ({tui.mode}，样本 {len(rows)} 条)'
    )
    render('🎭 疑似恶作剧 / 无效填答', counts, rules, ids, limit, verbose)


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
    rows = school_rows(tui)
    if rows is None:
        return

    counts, rules, ids = scan(rows, level_rule)
    if not counts:
        logger.info(f'🎉 未发现异常 ({tui.mode}，样本 {len(rows)} 条)')
        return

    logger.info(
        f'🔍 命中 {sum(counts.values())} 条 / {len(counts)} 个校名 ({tui.mode}，样本 {len(rows)} 条)'
    )
    render('🏫 疑似误填的中学 / 小学', counts, rules, ids, limit, verbose)


@check_group.command(name='merge')
@click.pass_obj
def check_merge(tui: UniInfoTUI) -> None:
    """分析数据中可合并的潜在相似大学名称"""
    rows = school_rows(tui)
    if rows is None:
        return
    logger.info(f'🔍 正在分析可合并的大学名称... ({tui.mode}，样本 {len(rows)} 条)')


@check_group.command(name='typo')
@click.option('--threshold', type=float, default=0.8, help='相似度阈值 (默认 0.8)')
@click.pass_obj
def check_typo(tui: UniInfoTUI, threshold: float) -> None:
    """基于阈值距离筛查名称错别字"""
    rows = school_rows(tui)
    if rows is None:
        return
    logger.info(
        f'🔍 正在以相似度 {threshold} 筛查错别字名称... ({tui.mode}，样本 {len(rows)} 条)'
    )


# 注册该 Click 顶层命令组到主框架路由中
register_plugin(check_group)

run_check = check_group
