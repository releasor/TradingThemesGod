"""全量多源竞速 full_race 单元测试。"""

from __future__ import annotations

import asyncio
from datetime import date

import pytest

from app.scrapers.draft_types import FullScrapeDraft
from app.scrapers.full_race import FullRaceManager


def _primary_draft(source: str = "primary") -> FullScrapeDraft:
    return FullScrapeDraft(
        source=source,
        trade_date=date(2026, 7, 27),
        themes=[{"code": "BK0001", "name": "主胜出"}],
        stocks_by_code={"BK0001": [{"code": "000001", "name": "平安"}]},
    )


def _fallback_draft(source: str = "fallback") -> FullScrapeDraft:
    return FullScrapeDraft(
        source=source,
        trade_date=date(2026, 7, 27),
        themes=[{"code": "BK0002", "name": "后备"}],
        stocks_by_code={},
    )


class _FakeScraper:
    def __init__(
        self,
        source: str,
        *,
        draft: FullScrapeDraft | None = None,
        delay: float = 0.0,
        fail: bool = False,
        hold_until: asyncio.Event | None = None,
    ):
        self.source_name = source
        self._draft = draft
        self._delay = delay
        self._fail = fail
        self._hold_until = hold_until
        self.commit_calls = 0
        self._commit = asyncio.Event()

    async def collect_full(self, cancel: asyncio.Event | None = None, params=None, **_kwargs):
        if self._hold_until is not None:
            await self._hold_until.wait()
        if self._delay:
            await asyncio.sleep(self._delay)
        if cancel is not None and cancel.is_set():
            raise asyncio.CancelledError()
        if self._fail:
            raise RuntimeError(f"{self.source_name} boom")
        assert self._draft is not None
        return self._draft

    async def commit_full(self, draft: FullScrapeDraft) -> int:
        self.commit_calls += 1
        self._commit.set()
        return 42

    async def close(self) -> None:
        return None


async def _wait_terminal(manager: FullRaceManager, race_id: str, timeout: float = 2.0):
    race = manager._races[race_id]
    assert race.task is not None
    await asyncio.wait_for(race.task, timeout=timeout)
    return manager.get_race(race_id)


@pytest.mark.asyncio
async def test_primary_wins_even_if_fallback_finished_first():
    """fallback 先完成也应继续等待；primary（含成分股）后到仍胜出。"""
    scrapers: dict[str, _FakeScraper] = {}

    def factory(source: str) -> _FakeScraper:
        if source == "fallback":
            sc = _FakeScraper(source, draft=_fallback_draft(source), delay=0.01)
        else:
            sc = _FakeScraper(source, draft=_primary_draft(source), delay=0.08)
        scrapers[source] = sc
        return sc

    manager = FullRaceManager(create_scraper=factory, persist_run=False)
    race_id = await manager.start_full_race(sources=["fallback", "primary"])
    state = await _wait_terminal(manager, race_id)

    assert state["status"] == "completed"
    assert state["winner"] == "primary"
    assert state["phase"] == "done"
    assert scrapers["primary"].commit_calls == 1
    assert scrapers["fallback"].commit_calls == 0


@pytest.mark.asyncio
async def test_cancel_before_commit_skips_commit_full():
    """采集中取消 → 不调用 commit_full。"""
    gate = asyncio.Event()
    scrapers: dict[str, _FakeScraper] = {}

    def factory(source: str) -> _FakeScraper:
        sc = _FakeScraper(source, draft=_primary_draft(source), hold_until=gate)
        scrapers[source] = sc
        return sc

    manager = FullRaceManager(create_scraper=factory, persist_run=False)
    race_id = await manager.start_full_race(sources=["primary"])

    for _ in range(50):
        snap = manager.get_race(race_id)
        if snap["sources"][0]["status"] == "running":
            break
        await asyncio.sleep(0.01)

    cancelled = await manager.cancel_race(race_id)
    assert cancelled["status"] == "cancelled"
    gate.set()
    state = await _wait_terminal(manager, race_id)

    assert state["status"] == "cancelled"
    assert scrapers["primary"].commit_calls == 0


@pytest.mark.asyncio
async def test_both_fail_status_failed():
    scrapers: dict[str, _FakeScraper] = {}

    def factory(source: str) -> _FakeScraper:
        sc = _FakeScraper(source, fail=True)
        scrapers[source] = sc
        return sc

    manager = FullRaceManager(create_scraper=factory, persist_run=False)
    race_id = await manager.start_full_race(sources=["a", "b"])
    state = await _wait_terminal(manager, race_id)

    assert state["status"] == "failed"
    assert state["winner"] is None
    assert state["error"]
    assert all(sc.commit_calls == 0 for sc in scrapers.values())


@pytest.mark.asyncio
async def test_winner_only_commit_full_called_once():
    scrapers: dict[str, _FakeScraper] = {}

    def factory(source: str) -> _FakeScraper:
        if source == "fast_primary":
            sc = _FakeScraper(source, draft=_primary_draft(source), delay=0.01)
        else:
            sc = _FakeScraper(source, draft=_primary_draft(source), delay=0.2)
        scrapers[source] = sc
        return sc

    manager = FullRaceManager(create_scraper=factory, persist_run=False)
    race_id = await manager.start_full_race(sources=["fast_primary", "slow_primary"])
    state = await _wait_terminal(manager, race_id)

    assert state["winner"] == "fast_primary"
    assert state["items_scraped"] == 42
    assert scrapers["fast_primary"].commit_calls == 1
    assert scrapers["slow_primary"].commit_calls == 0


@pytest.mark.asyncio
async def test_fallback_wins_when_primary_fails():
    scrapers: dict[str, _FakeScraper] = {}

    def factory(source: str) -> _FakeScraper:
        if source == "fallback":
            sc = _FakeScraper(source, draft=_fallback_draft(source), delay=0.01)
        else:
            sc = _FakeScraper(source, fail=True, delay=0.05)
        scrapers[source] = sc
        return sc

    manager = FullRaceManager(create_scraper=factory, persist_run=False)
    race_id = await manager.start_full_race(sources=["fallback", "primary"])
    state = await _wait_terminal(manager, race_id)

    assert state["status"] == "completed"
    assert state["winner"] == "fallback"
    assert scrapers["fallback"].commit_calls == 1
    assert scrapers["primary"].commit_calls == 0
