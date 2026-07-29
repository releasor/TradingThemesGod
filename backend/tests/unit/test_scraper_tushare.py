"""Tushare 爬虫单元测试。"""

from __future__ import annotations

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.core.config import Settings
from app.scrapers.draft_types import FullScrapeDraft
from app.scrapers.tushare_scraper import TushareScraper
from app.services.tushare_settings import (
    TushareRuntime,
    clear_tushare_runtime_cache,
    set_cached_tushare_runtime,
)


def _settings(**overrides: object) -> MagicMock:
    base = {
        "TUSHARE_API_URL": "",
        "TUSHARE_CONCEPT_APIS": "concept,ths_index,dc_index",
        "TUSHARE_CONCEPT_SRC": "ts",
        "TUSHARE_THS_INDEX_TYPE": "N",
        "TUSHARE_THS_INDEX_EXCHANGE": "A",
        "TUSHARE_MAX_RETRIES": 3,
    }
    base.update(overrides)
    mock = MagicMock(**base)
    mock.tushare_concept_api_list.return_value = [
        part.strip()
        for part in str(base["TUSHARE_CONCEPT_APIS"]).split(",")
        if part.strip()
    ]
    return mock


@pytest.fixture(autouse=True)
def _clear_runtime_cache():
    clear_tushare_runtime_cache()
    yield
    clear_tushare_runtime_cache()


@pytest.fixture
def scraper():
    return TushareScraper()


def test_normalize_concept_code(scraper):
    assert scraper._normalize_concept_code("885800.TI") == "TS885800"
    assert scraper._normalize_concept_code("TS885800") == "TS885800"
    assert scraper._normalize_concept_code("301558") == "TS301558"


def test_parse_concept_themes_from_concept_frame(scraper):
    frame = pd.DataFrame(
        [
            {"code": "TS001", "name": "人工智能"},
            {"code": "TS002", "name": "新能源"},
        ]
    )
    themes = scraper._parse_concept_themes(frame, api_name="concept")
    assert len(themes) == 2
    assert themes[0]["code"] == "TS001"
    assert themes[0]["source"] == "tushare"


def test_settings_parses_concept_api_list():
    settings = Settings(
        TUSHARE_CONCEPT_APIS=" ths_index , concept ",
        TUSHARE_ENABLED=True,
        TUSHARE_TOKEN="x",
    )
    assert settings.tushare_concept_api_list() == ["ths_index", "concept"]
    assert settings.tushare_ready() is True


def test_settings_tushare_not_ready_without_enable():
    settings = Settings(TUSHARE_ENABLED=False, TUSHARE_TOKEN="x")
    assert settings.tushare_ready() is False


@pytest.mark.asyncio
async def test_collect_full_requires_enabled(scraper):
    set_cached_tushare_runtime(
        TushareRuntime(enabled=False, token="dummy", from_db=True)
    )
    with (
        patch("app.scrapers.tushare_scraper.get_settings") as settings,
        patch("app.scrapers.tushare_scraper.AsyncSessionLocal") as session_cm,
    ):
        settings.return_value = _settings()
        session = AsyncMock()
        session_cm.return_value.__aenter__ = AsyncMock(return_value=session)
        session_cm.return_value.__aexit__ = AsyncMock(return_value=None)
        with patch(
            "app.services.tushare_settings.TushareSettingsService.resolve_runtime",
            new=AsyncMock(
                return_value=TushareRuntime(enabled=False, token="dummy", from_db=True)
            ),
        ):
            with pytest.raises(RuntimeError, match="未启用"):
                await scraper.collect_full()


@pytest.mark.asyncio
async def test_collect_full_requires_token(scraper):
    set_cached_tushare_runtime(
        TushareRuntime(enabled=True, token="", from_db=True)
    )
    with (
        patch("app.scrapers.tushare_scraper.get_settings") as settings,
        patch("app.scrapers.tushare_scraper.AsyncSessionLocal") as session_cm,
    ):
        settings.return_value = _settings()
        session = AsyncMock()
        session_cm.return_value.__aenter__ = AsyncMock(return_value=session)
        session_cm.return_value.__aexit__ = AsyncMock(return_value=None)
        with patch(
            "app.services.tushare_settings.TushareSettingsService.resolve_runtime",
            new=AsyncMock(
                return_value=TushareRuntime(enabled=True, token="", from_db=True)
            ),
        ):
            with pytest.raises(RuntimeError, match="Token"):
                await scraper.collect_full()


@pytest.mark.asyncio
async def test_collect_full_themes_only(scraper):
    frame = pd.DataFrame([{"code": "301558", "name": "人形机器人"}])
    set_cached_tushare_runtime(
        TushareRuntime(enabled=True, token="dummy-token", from_db=True)
    )
    with (
        patch("app.scrapers.tushare_scraper.get_settings") as settings,
        patch("app.scrapers.tushare_scraper.AsyncSessionLocal") as session_cm,
        patch.object(
            scraper,
            "_fetch_concept_frame_sync",
            return_value=(frame, "concept"),
        ),
    ):
        settings.return_value = _settings()
        session = AsyncMock()
        session_cm.return_value.__aenter__ = AsyncMock(return_value=session)
        session_cm.return_value.__aexit__ = AsyncMock(return_value=None)
        with patch(
            "app.services.tushare_settings.TushareSettingsService.resolve_runtime",
            new=AsyncMock(
                return_value=TushareRuntime(
                    enabled=True, token="dummy-token", from_db=True
                )
            ),
        ):
            draft = await scraper.collect_full()

    assert draft.source == "tushare"
    assert len(draft.themes) == 1
    assert draft.themes[0]["code"] == "TS301558"
    assert draft.themes[0]["name"] == "人形机器人"
    assert draft.stocks_by_code == {}
    assert isinstance(draft.trade_date, date)


@pytest.mark.asyncio
async def test_build_concept_attempts_respects_configured_order(scraper):
    pro = MagicMock()
    with patch("app.scrapers.tushare_scraper.get_settings") as settings:
        settings.return_value = _settings(TUSHARE_CONCEPT_APIS="dc_index,concept")
        attempts = scraper._build_concept_attempts(pro)
    assert [name for name, _ in attempts] == ["dc_index", "concept"]


@pytest.mark.asyncio
async def test_build_concept_attempts_rejects_unknown_api(scraper):
    pro = MagicMock()
    with patch("app.scrapers.tushare_scraper.get_settings") as settings:
        settings.return_value = _settings(TUSHARE_CONCEPT_APIS="foo")
        with pytest.raises(RuntimeError, match="不支持的 TUSHARE_CONCEPT_APIS"):
            scraper._build_concept_attempts(pro)


@pytest.mark.asyncio
async def test_commit_full_saves_themes(scraper):
    draft = FullScrapeDraft(
        source="tushare",
        trade_date=date(2026, 7, 28),
        themes=[{"name": "人形机器人", "code": "TS301558", "source": "tushare"}],
        stocks_by_code={},
    )
    scraper._save_themes = AsyncMock(return_value=1)
    assert await scraper.commit_full(draft) == 1
    scraper._save_themes.assert_awaited_once_with(draft.themes)


@pytest.mark.asyncio
async def test_collect_full_cancel_before_fetch(scraper):
    cancel = asyncio.Event()
    cancel.set()
    set_cached_tushare_runtime(
        TushareRuntime(enabled=True, token="dummy-token", from_db=True)
    )
    with pytest.raises(asyncio.CancelledError):
        await scraper.collect_full(cancel=cancel)
