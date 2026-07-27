"""题材与市场表现板块的分类规则。"""

from sqlalchemy.sql.elements import ColumnElement

from app.models.theme import Theme

MARKET_SIGNAL_CODES = frozenset(
    {
        "BK0815",  # 昨日涨停
        "BK0816",  # 昨日连板
        "BK0817",  # 昨日触板
        "BK0500",  # HS300_
        "BK0611",  # 上证50
        "BK0612",  # 上证180
        "BK0701",  # 中证500
        "BK0705",  # 上证380
        "BK1050",  # 昨日涨停_含一字
        "BK1051",  # 昨日连板_含一字
        "BK1112",  # 破净股
        "BK1139",  # 中特估
        "BK1630",  # 昨日首板
        "BK1631",  # 昨日炸板
        "BK1632",  # 昨日高换手
        "BK1633",  # 昨日高标
        "BK1635",  # 长期破净
        "BK1636",  # 红利破净股
        "BK1637",  # 东方财富热股
        "BK1638",  # 最近多板
        "BK1640",  # 价值股
        "BK1641",  # 红利股
        "BK1643",  # 小盘股
        "BK1645",  # 昨日打二板以上表现
        "BK1662",  # 权重股
        "BK1663",  # 大盘股
        "BK1664",  # 中盘股
        "BK1665",  # 大盘成长
        "BK1666",  # 大盘价值
        "BK1667",  # 小盘成长
        "BK1668",  # 小盘价值
        "BK1669",  # 中盘成长
        "BK1670",  # 中盘价值
        "BK1672",  # 破发股
        "BK1715",  # 趋势股
        "BK1716",  # 反转股
        "BK1717",  # 题材股
    }
)

# 财报预告、新高、破增发等行情指标板块（从涨跌幅/热门题材中独立展示）
INDICATOR_SIGNAL_CODES = frozenset(
    {
        "BK1673",  # 破增发价股
        "BK1674",  # 近期新高
        "BK1675",  # 历史新高
        "BK1676",  # 百日新高
        "BK1198",  # 2025三季报预增
        "BK1199",  # 2025三季报预减
        "BK1628",  # 2025三季报扭亏
        "BK1680",  # 2026一季报预增
        "BK1681",  # 2026一季报预减
        "BK1682",  # 2026一季报扭亏
        "BK1749",  # 2026中报预增
        "BK1750",  # 2026中报扭亏
        "BK1751",  # 2026中报首亏
        "BK1752",  # 2026中报预减
    }
)

_SORTED_MARKET_SIGNAL_CODES = tuple(sorted(MARKET_SIGNAL_CODES))
_SORTED_INDICATOR_SIGNAL_CODES = tuple(sorted(INDICATOR_SIGNAL_CODES))
_SORTED_NON_THEME_CODES = tuple(sorted(MARKET_SIGNAL_CODES | INDICATOR_SIGNAL_CODES))


def is_market_signal(code: str | None) -> bool:
    """判断板块代码是否属于市场表现。"""
    return code in MARKET_SIGNAL_CODES if code is not None else False


def is_indicator_signal(code: str | None) -> bool:
    """判断板块代码是否属于行情指标。"""
    return code in INDICATOR_SIGNAL_CODES if code is not None else False


def classify_board_kind(code: str | None) -> str:
    """返回板块种类：theme / market / indicator。"""
    if is_indicator_signal(code):
        return "indicator"
    if is_market_signal(code):
        return "market"
    return "theme"


def exclude_market_signals() -> ColumnElement[bool]:
    """构建排除市场表现与行情指标板块的查询条件。"""
    return Theme.code.not_in(_SORTED_NON_THEME_CODES)


def only_market_signals() -> ColumnElement[bool]:
    """构建仅包含市场表现板块的查询条件。"""
    return Theme.code.in_(_SORTED_MARKET_SIGNAL_CODES)


def only_indicator_signals() -> ColumnElement[bool]:
    """构建仅包含行情指标板块的查询条件。"""
    return Theme.code.in_(_SORTED_INDICATOR_SIGNAL_CODES)
