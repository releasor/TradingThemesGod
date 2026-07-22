import pytest

from app.scrapers.akshare import AKShareScraper
from app.scrapers.base import BaseScraper
from app.scrapers.eastmoney import EastMoneyScraper
from app.scrapers.registry import (
    ScraperRegistry,
    register_default_scrapers,
    scraper_registry,
)
from app.scrapers.sina import SinaFinanceScraper
from app.scrapers.ths import TongHuaShunScraper


class MockScraperA(BaseScraper):
    """测试爬虫 A"""
    source_name = "source_a"

    def parse(self, html: str) -> list[dict]:
        return [{"source": "a"}]

    async def save(self, data: list[dict]) -> int:
        return len(data)


class MockScraperB(BaseScraper):
    """测试爬虫 B"""
    source_name = "source_b"

    def parse(self, html: str) -> list[dict]:
        return [{"source": "b"}]

    async def save(self, data: list[dict]) -> int:
        return len(data)


class NotAScraper:
    """不是爬虫的类"""
    pass


@pytest.fixture
def registry():
    """创建一个新的注册表实例"""
    return ScraperRegistry()


def test_register_and_get(registry):
    """注册并获取爬虫类"""
    registry.register("a", MockScraperA)

    cls = registry.get("a")
    assert cls is MockScraperA


def test_get_nonexistent_returns_none(registry):
    """获取未注册的名称返回 None"""
    assert registry.get("nonexistent") is None


def test_register_rejects_non_subclass(registry):
    """注册非 BaseScraper 子类应抛出 TypeError"""
    with pytest.raises(TypeError, match="必须是 BaseScraper 的子类"):
        registry.register("bad", NotAScraper)  # type: ignore


def test_register_rejects_non_class(registry):
    """注册实例（非类）应抛出 TypeError"""
    with pytest.raises(TypeError, match="必须是 BaseScraper 的子类"):
        registry.register("bad", MockScraperA())  # type: ignore


def test_list_sources_empty(registry):
    """空注册表列出空列表"""
    assert registry.list_sources() == []


def test_list_sources_multiple(registry):
    """列出多个已注册的数据源"""
    registry.register("a", MockScraperA)
    registry.register("b", MockScraperB)

    sources = registry.list_sources()
    assert set(sources) == {"a", "b"}


def test_register_overwrites(registry):
    """重复注册同一名称应覆盖旧值"""
    registry.register("x", MockScraperA)
    registry.register("x", MockScraperB)

    assert registry.get("x") is MockScraperB
    assert registry.list_sources() == ["x"]


def test_register_logs(caplog):
    """注册时应记录日志"""
    import logging
    registry = ScraperRegistry()

    with caplog.at_level(logging.INFO):
        registry.register("eastmoney", MockScraperA)

    assert "eastmoney" in caplog.text
    assert "MockScraperA" in caplog.text


def test_register_default_scrapers(monkeypatch):
    """默认注册表应同时包含东方财富和同花顺爬虫。"""
    monkeypatch.setattr(scraper_registry, "_scrapers", {})

    register_default_scrapers()

    assert scraper_registry.get("eastmoney") is EastMoneyScraper
    assert scraper_registry.get("ths") is TongHuaShunScraper
    assert scraper_registry.get("local_chain") is None
    assert scraper_registry.get("akshare") is AKShareScraper
    assert scraper_registry.get("sina") is SinaFinanceScraper
