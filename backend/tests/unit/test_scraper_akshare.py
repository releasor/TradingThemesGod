"""AKShare 股票数据爬虫单元测试"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.scrapers.akshare import AKShareScraper


@pytest.fixture
def scraper():
    """创建爬虫实例"""
    return AKShareScraper()


@pytest.fixture
def sample_stock_data():
    """示例股票数据"""
    return [
        {
            "code": "600000",
            "name": "浦发银行",
            "industry": "银行",
            "market_cap": Decimal("1000000000.00"),
            "exchange": "SH",
        },
        {
            "code": "000001",
            "name": "平安银行",
            "industry": "银行",
            "market_cap": Decimal("800000000.00"),
            "exchange": "SZ",
        },
    ]


def test_detect_exchange_sh(scraper):
    """测试检测上海证券交易所"""
    assert scraper._detect_exchange("600000") == "SH"
    assert scraper._detect_exchange("601000") == "SH"
    assert scraper._detect_exchange("688000") == "SH"


def test_detect_exchange_sz(scraper):
    """测试检测深圳证券交易所"""
    assert scraper._detect_exchange("000001") == "SZ"
    assert scraper._detect_exchange("002000") == "SZ"
    assert scraper._detect_exchange("300000") == "SZ"


def test_detect_exchange_bj(scraper):
    """测试检测北京证券交易所"""
    assert scraper._detect_exchange("830000") == "BJ"
    assert scraper._detect_exchange("430000") == "BJ"


def test_detect_exchange_unknown(scraper):
    """测试检测未知交易所"""
    assert scraper._detect_exchange("999999") == ""
    assert scraper._detect_exchange("") == ""


def test_parse_returns_cached_data(scraper):
    """测试 parse 方法返回缓存数据"""
    scraper._stock_data = [{"code": "600000", "name": "浦发银行"}]
    result = scraper.parse("")
    assert result == [{"code": "600000", "name": "浦发银行"}]


def test_parse_returns_empty_when_no_cache(scraper):
    """测试 parse 方法在无缓存时返回空列表"""
    result = scraper.parse("")
    assert result == []


def test_source_name(scraper):
    """测试数据源名称"""
    assert scraper.source_name == "akshare"


def test_parse_tencent_quotes_maps_market_cap(scraper):
    text = (
        'v_sh600000="1~浦发银行~600000~8.92~8.89~8.92~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~'
        '20260716092604~0.03~0.34~0~0~0~0~0~0~0~0~0~0~0~2970.88~2970.88";'
    )

    result = scraper._parse_tencent_quotes(text)

    assert result["600000"] == Decimal("297088000000")


def test_normalize_spot_row_maps_live_fields(scraper):
    row = {"代码": "sh600000", "名称": "浦发银行", "最新价": 8.92, "涨跌幅": 0.34}

    result = scraper._normalize_spot_row(row)

    assert result == {
        "code": "600000",
        "name": "浦发银行",
        "current_price": Decimal("8.92"),
        "rise_fall_pct": Decimal("0.34"),
        "exchange": "SH",
    }


@pytest.mark.asyncio
async def test_fetch_stock_info_keeps_stocks_missing_from_live_snapshot(scraper):
    """实时快照缺股时，仍应使用完整股票目录补全基础数据。"""
    stock_catalog = pd.DataFrame(
        [
            {"code": "600000", "name": "浦发银行"},
            {"code": "600522", "name": "中天科技"},
        ]
    )
    live_snapshot = pd.DataFrame(
        [{"代码": "sh600000", "名称": "浦发银行", "最新价": 8.92, "涨跌幅": 0.34}]
    )

    with (
        patch("app.scrapers.akshare.ak.stock_info_a_code_name", return_value=stock_catalog),
        patch("app.scrapers.akshare.ak.stock_zh_a_spot", return_value=live_snapshot),
        patch.object(scraper, "_fetch_sina_industries", return_value=({}, {})),
        patch.object(
            scraper,
            "_fetch_tencent_market_caps",
            return_value={"600522": Decimal("132525000000")},
        ),
    ):
        result = await scraper.fetch_stock_info()

    by_code = {stock["code"]: stock for stock in result}
    assert set(by_code) == {"600000", "600522"}
    assert by_code["600522"]["name"] == "中天科技"
    assert by_code["600522"]["market_cap"] == Decimal("132525000000")
    assert by_code["600522"]["current_price"] is None


@pytest.mark.asyncio
async def test_save_with_new_stock(scraper):
    """测试保存新股票"""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    with patch("app.scrapers.akshare.AsyncSessionLocal") as mock_local:
        mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

        data = [
            {
                "code": "600000",
                "name": "浦发银行",
                "industry": "银行",
                "market_cap": Decimal("1000000000.00"),
                "exchange": "SH",
            }
        ]

        result = await scraper.save(data)
        assert result == 1


@pytest.mark.asyncio
async def test_save_with_existing_stock(scraper):
    """测试更新已存在的股票"""
    mock_stock = MagicMock()
    mock_stock.code = "600000"
    mock_stock.name = "浦发银行"

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_stock)))

    with patch("app.scrapers.akshare.AsyncSessionLocal") as mock_local:
        mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

        data = [
            {
                "code": "600000",
                "name": "浦发银行",
                "industry": "银行",
                "market_cap": Decimal("1200000000.00"),
                "exchange": "SH",
            }
        ]

        result = await scraper.save(data)
        assert result == 1


@pytest.mark.asyncio
async def test_save_with_empty_data(scraper):
    """测试保存空数据"""
    mock_session = AsyncMock()

    with patch("app.scrapers.akshare.AsyncSessionLocal") as mock_local:
        mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await scraper.save([])
        assert result == 0


@pytest.mark.asyncio
async def test_save_handles_exception(scraper):
    """测试保存时处理异常"""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=Exception("Database error"))

    with patch("app.scrapers.akshare.AsyncSessionLocal") as mock_local:
        mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

        data = [
            {
                "code": "600000",
                "name": "浦发银行",
                "industry": "银行",
                "market_cap": Decimal("1000000000.00"),
                "exchange": "SH",
            }
        ]

        result = await scraper.save(data)
        # 异常被捕获，保存计数为 0
        assert result == 0
