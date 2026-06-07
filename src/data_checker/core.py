import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uniinfo_editor import UniInfoTUI

# 检查可能的恶作剧名称
# 检查可能的中学/小学名称
# 检查可能的可以合并的大学名称
# 检查可能的可以错别字名称


def run_check(tui: 'UniInfoTUI', arg_str: str):
    """[插件] desc here"""
    logger = logging.getLogger('uniinfo')
    logger.info('Your First Plugin')
    logger.info(arg_str)
