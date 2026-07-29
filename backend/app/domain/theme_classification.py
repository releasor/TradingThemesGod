"""题材与市场表现板块的分类规则。

东方财富以 BK 代码区分；同花顺 / 其它源代码不同，按与东财一致的板块名称区分。
"""

from __future__ import annotations

from sqlalchemy import or_
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
        "BK1633",  # 昨日高标 / 昨日高振幅
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

# 与东财板块名称对齐的子串（覆盖同花顺 THS*、含一字变体、带前缀名称）
MARKET_SIGNAL_NAME_MARKERS = frozenset(
    {
        "昨日涨停",
        "昨日连板",
        "昨日触板",
        "昨日首板",
        "昨日炸板",
        "昨日高换手",
        "昨日高标",
        "昨日高振幅",
        "昨日打二板",
        "最近多板",
        "破净股",
        "长期破净",
        "红利破净",
        "破发股",
        "中特估",
        "价值股",
        "红利股",
        "小盘股",
        "大盘股",
        "中盘股",
        "大盘成长",
        "大盘价值",
        "小盘成长",
        "小盘价值",
        "中盘成长",
        "中盘价值",
        "权重股",
        "趋势股",
        "反转股",
        "题材股",
        "东方财富热股",
        "上证50",
        "上证180",
        "上证380",
        "中证500",
        "HS300",
        "沪深300",
    }
)

INDICATOR_SIGNAL_NAME_MARKERS = frozenset(
    {
        "破增发",
        "近期新高",
        "历史新高",
        "百日新高",
        "季报预增",
        "季报预减",
        "季报扭亏",
        "中报预增",
        "中报预减",
        "中报扭亏",
        "中报首亏",
        "年报预增",
        "年报预减",
        "年报扭亏",
        "年报首亏",
    }
)

_SORTED_MARKET_SIGNAL_CODES = tuple(sorted(MARKET_SIGNAL_CODES))
_SORTED_INDICATOR_SIGNAL_CODES = tuple(sorted(INDICATOR_SIGNAL_CODES))
_SORTED_NON_THEME_CODES = tuple(sorted(MARKET_SIGNAL_CODES | INDICATOR_SIGNAL_CODES))
_SORTED_MARKET_NAME_MARKERS = tuple(sorted(MARKET_SIGNAL_NAME_MARKERS, key=len, reverse=True))
_SORTED_INDICATOR_NAME_MARKERS = tuple(
    sorted(INDICATOR_SIGNAL_NAME_MARKERS, key=len, reverse=True)
)
_SORTED_NON_THEME_NAME_MARKERS = tuple(
    sorted(MARKET_SIGNAL_NAME_MARKERS | INDICATOR_SIGNAL_NAME_MARKERS, key=len, reverse=True)
)


def _normalize_board_name(name: str | None) -> str:
    if not name:
        return ""
    return name.strip().rstrip("_")


def _name_has_marker(name: str | None, markers: frozenset[str] | tuple[str, ...]) -> bool:
    normalized = _normalize_board_name(name)
    if not normalized:
        return False
    return any(marker in normalized for marker in markers)


def is_market_signal(code: str | None = None, name: str | None = None) -> bool:
    """判断板块是否属于市场表现（BK 码或与东财同名）。"""
    if code is not None and code in MARKET_SIGNAL_CODES:
        return True
    return _name_has_marker(name, MARKET_SIGNAL_NAME_MARKERS)


def is_indicator_signal(code: str | None = None, name: str | None = None) -> bool:
    """判断板块是否属于行情指标（BK 码或与东财同名）。"""
    if code is not None and code in INDICATOR_SIGNAL_CODES:
        return True
    return _name_has_marker(name, INDICATOR_SIGNAL_NAME_MARKERS)


def classify_board_kind(code: str | None = None, name: str | None = None) -> str:
    """返回板块种类：theme / market / indicator。"""
    if is_indicator_signal(code, name):
        return "indicator"
    if is_market_signal(code, name):
        return "market"
    return "theme"


def _name_marker_clause(markers: tuple[str, ...]) -> ColumnElement[bool]:
    return or_(*(Theme.name.contains(marker) for marker in markers))


def exclude_market_signals() -> ColumnElement[bool]:
    """构建排除市场表现与行情指标板块的查询条件。"""
    return ~or_(
        Theme.code.in_(_SORTED_NON_THEME_CODES),
        _name_marker_clause(_SORTED_NON_THEME_NAME_MARKERS),
    )


def only_market_signals() -> ColumnElement[bool]:
    """构建仅包含市场表现板块的查询条件。"""
    return or_(
        Theme.code.in_(_SORTED_MARKET_SIGNAL_CODES),
        _name_marker_clause(_SORTED_MARKET_NAME_MARKERS),
    )


def only_indicator_signals() -> ColumnElement[bool]:
    """构建仅包含行情指标板块的查询条件。"""
    return or_(
        Theme.code.in_(_SORTED_INDICATOR_SIGNAL_CODES),
        _name_marker_clause(_SORTED_INDICATOR_NAME_MARKERS),
    )
