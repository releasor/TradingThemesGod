"""AKShare 股票数据爬虫单元测试"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

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
