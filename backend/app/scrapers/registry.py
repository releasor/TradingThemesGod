"""爬虫注册表

管理所有已注册的爬虫类，通过名称查找。
"""

from typing import Type

from app.core.logging import get_logger
from app.scrapers.base import BaseScraper

logger = get_logger(__name__)


class ScraperRegistry:
    """爬虫注册表

    使用方式:
        registry = ScraperRegistry()
        registry.register("eastmoney", EastMoneyScraper)
        scraper_cls = registry.get("eastmoney")
    """

    def __init__(self):
        self._scrapers: dict[str, Type[BaseScraper]] = {}

    def register(self, name: str, scraper_class: Type[BaseScraper]) -> None:
        """注册爬虫类

        Args:
            name: 数据源名称
            scraper_class: 爬虫类（必须继承 BaseScraper）

        Raises:
            TypeError: 如果 scraper_class 不是 BaseScraper 的子类
        """
        if not (isinstance(scraper_class, type) and issubclass(scraper_class, BaseScraper)):
            raise TypeError(f"{scraper_class} 必须是 BaseScraper 的子类")
        self._scrapers[name] = scraper_class
        logger.info(f"已注册爬虫: {name} -> {scraper_class.__name__}")

    def get(self, name: str) -> Type[BaseScraper] | None:
        """获取爬虫类

        Args:
            name: 数据源名称

        Returns:
            爬虫类，如果未注册则返回 None
        """
        return self._scrapers.get(name)

    def list_sources(self) -> list[str]:
        """列出所有已注册的数据源名称"""
        return list(self._scrapers.keys())


# 全局注册表实例
scraper_registry = ScraperRegistry()


def register_default_scrapers() -> None:
    """注册默认爬虫"""
    from app.scrapers.eastmoney import EastMoneyScraper

    scraper_registry.register("eastmoney", EastMoneyScraper)
    logger.info("已注册默认爬虫: eastmoney")
