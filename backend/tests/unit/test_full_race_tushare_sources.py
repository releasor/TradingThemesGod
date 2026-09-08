"""default_full_race_sources 对 Tushare ready 的回归。"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.scrapers.base import BaseScraper
from app.scrapers.draft_types import FullScrapeDraft
from app.scrapers.full_race import default_full_race_sources
from app.scrapers.registry import scraper_registry


class _CollectFullScraper(BaseScraper):
    source_name = "mock"

    def parse(self, html: str) -> list[dict]:
        return []

    async def save(self, data: list[dict]) -> int:
        return 0

    async def collect_full(self, **_kwargs) -> FullScrapeDraft:
        return FullScrapeDraft(source=self.source_name, trade_date=None, themes=[])


def test_default_full_race_includes_tushare_when_ready(monkeypatch):
    monkeypatch.setattr(
        "app.services.tushare_settings.get_cached_tushare_runtime",
        lambda: SimpleNamespace(ready=True),
    )
    monkeypatch.setattr(
        "app.scrapers.full_race.list_registered_scraper_sources",
        lambda dashboard_only=True: [
            SimpleNamespace(id="eastmoney"),
            SimpleNamespace(id="tushare"),
        ],
    )
    scraper_registry.register("eastmoney", _CollectFullScraper)
    scraper_registry.register("tushare", _CollectFullScraper)
    assert "tushare" in default_full_race_sources()
    assert "eastmoney" in default_full_race_sources()


def test_default_full_race_skips_tushare_when_not_ready(monkeypatch):
    monkeypatch.setattr(
        "app.services.tushare_settings.get_cached_tushare_runtime",
        lambda: SimpleNamespace(ready=False),
    )
    monkeypatch.setattr(
        "app.scrapers.full_race.list_registered_scraper_sources",
        lambda dashboard_only=True: [
            SimpleNamespace(id="eastmoney"),
            SimpleNamespace(id="tushare"),
        ],
    )
    scraper_registry.register("eastmoney", _CollectFullScraper)
    scraper_registry.register("tushare", _CollectFullScraper)
    sources = default_full_race_sources()
    assert "tushare" not in sources
    assert "eastmoney" in sources


def test_default_create_scraper_uses_factory(monkeypatch):
    from app.scrapers.full_race import FullRaceManager

    created = {}

    def fake_create(source: str):
        created["source"] = source
        return MagicMock()

    monkeypatch.setattr(
        "app.scrapers.full_race.create_scraper_from_settings",
        fake_create,
    )
    FullRaceManager._default_create_scraper("eastmoney")
    assert created["source"] == "eastmoney"
