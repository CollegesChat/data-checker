import logging
from collections import Counter

from rich.console import Console
from rich.table import Table

logger = logging.getLogger('uniinfo')


def render(
    title: str,
    counts: Counter[str],
    rules: dict[str, str],
    ids: dict[str, list[str]],
    limit: int,
    verbose: bool,
    rule_header: str = '规则',
) -> None:
    """逐校名一行：学校名 / 次数 / 规则 / 样例 ID"""
    ordered = sorted(counts, key=lambda n: (-counts[n], n))
    shown = ordered if limit == 0 else ordered[:limit]

    table = Table(title=title, show_header=True, box=None)
    table.add_column(
        '学校名', style='bold', max_width=40, overflow='ellipsis', no_wrap=True
    )
    table.add_column('次数', justify='right')
    table.add_column(rule_header)
    table.add_column('样例 ID', style='dim')
    for name in shown:
        sample = ids[name] if verbose else ids[name][:3]
        table.add_row(name, str(counts[name]), rules[name], ' '.join(sample))
    Console().print(table)

    if len(shown) < len(ordered):
        logger.info(f'仅显示前 {len(shown)} / {len(ordered)} 个，--limit 0 查看全部')


def render_groups(
    title: str,
    groups: list[tuple[str, list[str]]],
    counts: Counter[str],
    ids: dict[str, list[str]],
    limit: int,
    verbose: bool,
) -> None:
    """逐组一行：建议写法 / 次数 / 其余异写 / 样例 ID"""
    shown = groups if limit == 0 else groups[:limit]

    table = Table(title=title, show_header=True, box=None)
    table.add_column(
        '建议写法', style='bold', max_width=36, overflow='ellipsis', no_wrap=True
    )
    table.add_column('次数', justify='right')
    table.add_column('异写', max_width=44, overflow='ellipsis', no_wrap=True)
    table.add_column('样例 ID', style='dim')
    for canon, members in shown:
        others = ' | '.join(f'{m}({counts[m]})' for m in members if m != canon)
        sample = ids[canon] if verbose else ids[canon][:3]
        table.add_row(canon, str(counts[canon]), others, ' '.join(sample))
    Console().print(table)

    if len(shown) < len(groups):
        logger.info(f'仅显示前 {len(shown)} / {len(groups)} 组，--limit 0 查看全部')
