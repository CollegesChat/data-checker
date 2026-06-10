import logging
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from uniinfo_editor import UniInfoTUI

from uniinfo_editor import register_plugin


# =====================================================================
# ⚙️ 用 Click 构建多级子命令组
# =====================================================================
@click.group(name='check')
def check_group() -> None:
    """大学数据多维度异常校验 (joke/school/merge/typo)"""
    pass


@check_group.command(name='joke')
@click.pass_obj
def check_joke(tui: UniInfoTUI) -> None:
    """扫描恶作剧大学名称"""
    logger = logging.getLogger('uniinfo')
    if not tui.data:
        logger.error('❌ 内存中未发现任何数据，请先执行 `load`。')
        return
    logger.info('🔍 正在扫描恶作剧名称...')


@check_group.command(name='school')
@click.pass_obj
def check_school(tui: UniInfoTUI) -> None:
    """筛查误填的中学、小学名称"""
    logger = logging.getLogger('uniinfo')
    if not tui.data:
        logger.error('❌ 内存中未发现任何数据，请先执行 `load`。')
        return
    logger.info('🔍 正在筛查误填的中学、小学名称...')


@check_group.command(name='merge')
@click.pass_obj
def check_merge(tui: UniInfoTUI) -> None:
    """分析数据中可合并的潜在相似大学名称"""
    logger = logging.getLogger('uniinfo')
    if not tui.data:
        logger.error('❌ 内存中未发现任何数据，请先执行 `load`。')
        return
    logger.info('🔍 正在分析可合并的大学名称...')


@check_group.command(name='typo')
@click.option(
    '--threshold', type=float, default=0.8, help='相似度阈值 (默认 0.8)'
)
@click.pass_obj
def check_typo(tui: UniInfoTUI, threshold: float) -> None:
    """基于阈值距离筛查名称错别字"""
    logger = logging.getLogger('uniinfo')
    if not tui.data:
        logger.error('❌ 内存中未发现任何数据，请先执行 `load`。')
        return
    logger.info(f'🔍 正在以相似度 {threshold} 筛查错别字名称...')


# 注册该 Click 顶层命令组到主框架路由中
register_plugin(check_group)

run_check = check_group
