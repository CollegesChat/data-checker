import re
from functools import lru_cache

import opencc

_T2S = opencc.OpenCC('t2s')

PAREN = re.compile(r'[（(\[【][^）)\]】]*[）)\]】]')
NOISE = re.compile(r'[\s·・\-—_（）()【】\[\]]')
TRAIL = re.compile(r'[，。、；：,.]+$')

# 校區後綴：主體已完整（学/院/校 结尾）后，再跟 0~4 字 + 校区|校园|分校|本部
CAMPUS = re.compile(r'(?<=[学院校])[^校区]{0,4}(?:校区|校區|校园|校園|分校|本部)$')

# 層級詞：差異段裡出現這些代表「另一所學校」而非錯字
TIER = re.compile(
    r'大学|大學|职业|職業|技术|技術|师范|師範|专科|專科|高等|技工|技师|国际|國際'
)

# 校址詞：差異段裡出現這些代表「另一個校區」，屬 merge 不是 typo
PLACE = re.compile(r'校区|校區|分校|本部|校园|校園|小区|小區|园区|園區|院区|院區')


@lru_cache(maxsize=None)
def norm(name: str) -> str:
    """繁體轉簡體 → 去括號 → 去空白與連字號 → 去結尾句讀 → 去校區後綴"""
    s = _T2S.convert(name)
    s = PAREN.sub('', s)
    s = NOISE.sub('', s)
    s = TRAIL.sub('', s)
    return CAMPUS.sub('', s)


@lru_cache(maxsize=None)
def core_name(name: str) -> str:
    """再剝掉 大学/学院/学校：只用於提示，不足以自動合併"""
    return re.sub(r'(?:大学|大學|学院|學院|学校|學校)+$', '', norm(name))
