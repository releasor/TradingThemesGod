"""新浪财经事件爬虫单元测试"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.scrapers.sina import SinaFinanceScraper


@pytest.fixture
def scraper():
    """创建爬虫实例"""
    return SinaFinanceScraper()


@pytest.fixture
def sample_html():
    """示例 HTML 内容"""
    return """
    <html>
    <body>
        <div class="news-list">
            <a href="http://news.sina.com.cn/1">公司发布重大公告</a>
            <span>2024-01-15</span>
            <a href="http://news.sina.com.cn/2">行业政策变化分析</a>
            <span>2024-01-14</span>
            <a href="http://news.sina.com.cn/3">季度财报解读</a>
            <span>2024-01-13</span>
        </div>
    </body>
    </html>
    """


def test_parse_returns_list(scraper, sample_html):
    """测试 parse 方法返回列表"""
    result = scraper.parse(sample_html)
    assert isinstance(result, list)


def test_parse_extracts_events(scraper, sample_html):
    """测试 parse 方法提取事件数据"""
    result = scraper.parse(sample_html)
    # 应该提取到事件
    assert len(result) > 0


def test_parse_handles_empty_html(scraper):
    """测试 parse 方法处理空 HTML"""
    result = scraper.parse("")
    assert result == []


def test_parse_handles_none_html(scraper):
    """测试 parse 方法处理 None"""
    result = scraper.parse(None)
    assert result == []


def test_classify_event_news(scraper):
    """测试事件分类 - 新闻"""
    result = scraper._classify_event("公司发布公告")
    assert result == "announcement"


def test_classify_event_policy(scraper):
    """测试事件分类 - 政策"""
    result = scraper._classify_event("政策变化分析")
    assert result == "policy"


def test_classify_event_industry(scraper):
    """测试事件分类 - 行业"""
    result = scraper._classify_event("行业发展趋势")
    assert result == "industry"


def test_classify_event_default(scraper):
    """测试事件分类 - 默认"""
    result = scraper._classify_event("普通新闻标题")
    assert result == "news"


def test_parse_date_valid(scraper):
    """测试解析有效日期"""
    result = scraper._parse_date("2024-01-15")
    assert result is not None
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 15


def test_parse_date_invalid(scraper):
    """测试解析无效日期"""
    result = scraper._parse_date("invalid-date")
    assert result is None


def test_parse_date_empty(scraper):
    """测试解析空日期"""
    result = scraper._parse_date("")
    assert result is None


def test_source_name(scraper):
    """测试数据源名称"""
    assert scraper.source_name == "sina"


def test_normalize_stock_symbol(scraper):
    assert scraper._normalize_stock_symbol("600000") == "sh600000"
    assert scraper._normalize_stock_symbol("000001") == "sz000001"
    assert scraper._normalize_stock_symbol("920000") == "bj920000"
    assert scraper._normalize_stock_symbol("sh600000") == "sh600000"


@pytest.mark.asyncio
async def test_save_with_valid_data(scraper):
    """测试保存有效数据"""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    with patch("app.scrapers.sina.AsyncSessionLocal") as mock_local:
        mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

        data = [
            {
                "title": "测试事件",
                "content": "事件内容",
                "source": "新浪财经",
                "event_type": "news",
                "published_at": datetime(2024, 1, 15, tzinfo=UTC),
                "stock_id": 1,
            }
        ]

        result = await scraper.save(data)
        assert result == 1


@pytest.mark.asyncio
async def test_save_with_empty_data(scraper):
    """测试保存空数据"""
    mock_session = AsyncMock()

    with patch("app.scrapers.sina.AsyncSessionLocal") as mock_local:
        mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_local.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await scraper.save([])
        assert result == 0


@pytest.mark.asyncio
async def test_save_deduplicates_events_per_stock(scraper):
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
    )

    with patch("app.scrapers.sina.AsyncSessionLocal") as mock_local:
        mock_local.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_local.return_value.__aexit__ = AsyncMock(return_value=None)
        await scraper.save(
            [
                {
                    "title": "同一条市场新闻",
                    "published_at": datetime(2026, 7, 16, tzinfo=UTC),
                    "stock_id": 100,
                },
                {
                    "title": "同一条市场新闻",
                    "published_at": datetime(2026, 7, 16, tzinfo=UTC),
                    "stock_id": 200,
                },
            ]
        )

    query = mock_session.execute.await_args.args[0]
    assert "events.stock_id" in str(query)


def test_extract_news_items(scraper, sample_html):
    """测试提取新闻条目"""
    items = scraper._extract_news_items(sample_html)
    assert isinstance(items, list)
