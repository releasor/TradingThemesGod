"""市场表现与行情指标板块分类测试。"""

from sqlalchemy import select
from sqlalchemy.dialects import mysql

from app.domain.theme_classification import (
    INDICATOR_SIGNAL_CODES,
    classify_board_kind,
    exclude_market_signals,
    is_indicator_signal,
    is_market_signal,
    only_indicator_signals,
    only_market_signals,
)
from app.models.theme import Theme

STYLE_FACTOR_CODES = {
    "BK1112",
    "BK1139",
    "BK1635",
    "BK1636",
    "BK1640",
    "BK1641",
    "BK1643",
    "BK1662",
    "BK1663",
    "BK1664",
    "BK1665",
    "BK1666",
    "BK1667",
    "BK1668",
    "BK1669",
    "BK1670",
    "BK1672",
}

INDEX_BOARD_CODES = {
    "BK0500",
    "BK0611",
    "BK0612",
    "BK0701",
    "BK0705",
}

INDICATOR_CODES = {
    "BK1673",
    "BK1674",
    "BK1675",
    "BK1676",
    "BK1198",
    "BK1199",
    "BK1628",
    "BK1680",
    "BK1681",
    "BK1682",
    "BK1749",
    "BK1750",
    "BK1751",
    "BK1752",
}


def _compile(condition):
    return (
        select(Theme)
        .where(condition)
        .compile(dialect=mysql.dialect(paramstyle="named"))
    )


def test_known_market_signal_codes_are_classified():
    for code in ("BK0815", "BK0816", "BK1631", "BK1638", "BK1715"):
        assert is_market_signal(code) is True


def test_style_factor_codes_are_classified_as_market_signals():
    assert all(is_market_signal(code) for code in STYLE_FACTOR_CODES)


def test_index_board_codes_are_classified_as_market_signals():
    assert all(is_market_signal(code) for code in INDEX_BOARD_CODES)


def test_indicator_signal_codes_are_classified():
    assert INDICATOR_CODES == set(INDICATOR_SIGNAL_CODES)
    assert all(is_indicator_signal(code) for code in INDICATOR_CODES)
    assert is_indicator_signal(None) is False
    assert is_market_signal("BK1676") is False
    assert is_indicator_signal("BK0815") is False


def test_regular_theme_code_is_not_classified_as_market_signal():
    assert is_market_signal("BK1234") is False
    assert is_market_signal("BK0683") is False
    assert is_market_signal(None) is False
    assert is_indicator_signal("BK0683") is False


def test_name_based_classification_for_non_bk_sources():
    assert is_indicator_signal("THS309265", "2026一季报预增") is True
    assert is_indicator_signal("THS309267", "2026中报预增") is True
    assert is_market_signal("THS309062", "同花顺中特估100") is True
    assert is_market_signal("THS000001", "昨日涨停_含一字") is True
    assert is_indicator_signal("THS000002", "百日新高") is True
    assert is_market_signal("THS308718", "同花顺漂亮100") is False
    assert is_indicator_signal("THS301558", "人工智能") is False
    assert classify_board_kind("THS309265", "2026一季报预增") == "indicator"
    assert classify_board_kind("THS309062", "同花顺中特估100") == "market"
    assert classify_board_kind("THS301558", "人工智能") == "theme"


def test_exclusion_condition_compiles_with_code_and_name_markers():
    compiled = _compile(exclude_market_signals())
    sql = str(compiled)

    assert "NOT" in sql
    assert "LIKE" in sql.upper()
    param_values = set()
    for value in compiled.params.values():
        if isinstance(value, (list, tuple, set)):
            param_values.update(value)
        else:
            param_values.add(value)
    assert "BK0815" in param_values
    assert STYLE_FACTOR_CODES <= param_values
    assert INDEX_BOARD_CODES <= param_values
    assert INDICATOR_CODES <= param_values
    assert any("昨日涨停" in str(v) for v in param_values)
    assert any("季报预增" in str(v) for v in param_values)


def test_inclusion_condition_compiles_to_in():
    compiled = _compile(only_market_signals())

    sql = str(compiled)
    assert " IN " in sql
    codes = set(next(iter(compiled.params.values())))
    assert "BK0815" in codes
    assert STYLE_FACTOR_CODES <= codes
    assert INDEX_BOARD_CODES <= codes
    assert "BK1676" not in codes
    assert any("中特估" in str(v) for v in compiled.params.values())


def test_indicator_inclusion_condition_compiles_to_in():
    compiled = _compile(only_indicator_signals())

    sql = str(compiled)
    assert " IN " in sql
    codes = set(next(iter(compiled.params.values())))
    assert INDICATOR_CODES == codes
    assert "BK0815" not in codes
    assert any("中报预增" in str(v) for v in compiled.params.values())


def test_classify_board_kind():
    assert classify_board_kind("BK1645") == "market"
    assert classify_board_kind("BK1633") == "market"
    assert classify_board_kind("BK1676") == "indicator"
    assert classify_board_kind("BK0683") == "theme"
    assert classify_board_kind(None) == "theme"
