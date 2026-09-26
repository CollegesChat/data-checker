import re

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


def joke_rule(name: str) -> str | None:
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


def level_rule(name: str) -> str | None:
    return '基础教育' if SCHOOL_LEVEL.search(name) else None
