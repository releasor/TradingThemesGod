"""爬虫注册表单元测试

测试爬虫类注册、查找和验证功能。
"""

import pytest
from typing import Any

from app.scrapers.registry import ScraperRegistry
from app.scrapers.base import BaseScraper


class MockScraper(BaseScraper):
    """用于测试的模拟爬虫"""
    source_name = "mock"

    def parse(self, html: str) -> list[dict[str, Any]]:
        return [{"title": "test", "content": html}]

    async def save(self, data: list[dict[str, Any]]) -> int:
        return len(data)


class AnotherMockScraper(BaseScraper):
    """另一个模拟爬虫"""
    source_name = "another_mock"

    def parse(self, html: str) -> list[dict[str, Any]]:
        return []

    async def save(self, data: list[dict[str, Any]]) -> int:
        return 0


class NotAScraper:
    """非爬虫类，用于测试类型检查"""
    pass


class TestScraperRegistry:
    """ScraperRegistry 测试"""

    def test_register_valid_scraper(self):
        """测试注册有效的爬虫类"""
        registry = ScraperRegistry()
        registry.register("mock", MockScraper)
        assert registry.get("mock") is MockScraper

    def test_register_invalid_class_raises_type_error(self):
        """测试注册非 BaseScraper 子类时抛出 TypeError"""
        registry = ScraperRegistry()
        with pytest.raises(TypeError, match="BaseScraper"):
            registry.register("invalid", NotAScraper)

    def test_register_non_class_raises_type_error(self):
        """测试注册非类对象时抛出 TypeError"""
        registry = ScraperRegistry()
        with pytest.raises(TypeError):
            registry.register("string", "not_a_class")

    def test_register_multiple_scrapers(self):
        """测试注册多个爬虫"""
        registry = ScraperRegistry()
        registry.register("mock1", MockScraper)
        registry.register("mock2", AnotherMockScraper)
        assert registry.get("mock1") is MockScraper
        assert registry.get("mock2") is AnotherMockScraper

    def test_register_overwrites_existing(self):
        """测试同名注册覆盖已有爬虫"""
        registry = ScraperRegistry()
        registry.register("mock", MockScraper)
        registry.register("mock", AnotherMockScraper)
        assert registry.get("mock") is AnotherMockScraper

    def test_get_unregistered_returns_none(self):
        """测试获取未注册的爬虫返回 None"""
        registry = ScraperRegistry()
        assert registry.get("nonexistent") is None

    def test_list_sources_empty(self):
        """测试空注册表列出数据源为空列表"""
        registry = ScraperRegistry()
        assert registry.list_sources() == []

    def test_list_sources_with_registered(self):
        """测试列出已注册的数据源"""
        registry = ScraperRegistry()
        registry.register("eastmoney", MockScraper)
        registry.register("sina", AnotherMockScraper)
        sources = registry.list_sources()
        assert "eastmoney" in sources
        assert "sina" in sources
        assert len(sources) == 2

    def test_initial_state_is_empty(self):
        """测试初始状态为空"""
        registry = ScraperRegistry()
        assert registry.list_sources() == []
        assert registry.get("anything") is None
