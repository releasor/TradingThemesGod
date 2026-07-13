"""BaseScraper 单元测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.scrapers.base import BaseScraper


class MockScraper(BaseScraper):
    """测试用爬虫"""

    source_name = "test"

    def parse(self, html: str) -> list[dict]:
        return [{"title": "test", "content": html[:10]}]

    async def save(self, data: list[dict]) -> int:
        return len(data)


@pytest.fixture
def mock_middleware():
    """模拟反爬虫中间件"""
    middleware = AsyncMock()
    mock_response = MagicMock()
    mock_response.text = "<html>test content</html>"
    mock_response.raise_for_status = MagicMock()
    middleware.get = AsyncMock(return_value=mock_response)
    return middleware


@pytest.mark.asyncio
async def test_base_scraper_lifecycle(mock_middleware):
    """测试爬虫生命周期: fetch → parse → save"""
    scraper = MockScraper(middleware=mock_middleware)

    data, count = await scraper.run("http://example.com")

    assert len(data) == 1
    assert data[0]["title"] == "test"
    assert count == 1
    mock_middleware.get.assert_called_once_with("http://example.com", params=None)


@pytest.mark.asyncio
async def test_base_scraper_fetch(mock_middleware):
    """测试 fetch 方法"""
    scraper = MockScraper(middleware=mock_middleware)

    html = await scraper.fetch("http://example.com", {"key": "value"})

    assert html == "<html>test content</html>"
    mock_middleware.get.assert_called_once_with(
        "http://example.com", params={"key": "value"}
    )


@pytest.mark.asyncio
async def test_base_scraper_close(mock_middleware):
    """测试 close 方法"""
    scraper = MockScraper(middleware=mock_middleware)

    await scraper.close()

    mock_middleware.close.assert_called_once()


@pytest.mark.asyncio
async def test_base_scraper_run_with_params(mock_middleware):
    """测试带参数的 run 方法"""
    scraper = MockScraper(middleware=mock_middleware)

    data, count = await scraper.run("http://example.com", {"page": 1})

    assert count == 1
    mock_middleware.get.assert_called_once_with(
        "http://example.com", params={"page": 1}
    )
