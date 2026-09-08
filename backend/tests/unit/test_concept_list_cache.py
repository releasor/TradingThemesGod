"""concept_list_cache 单元测试。"""

import asyncio

import pytest

from app.scrapers import concept_list_cache as cache


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.asyncio
async def test_get_or_fetch_hits_within_ttl():
    calls = {"n": 0}

    async def fetch():
        calls["n"] += 1
        return {"ok": calls["n"]}

    first = await cache.get_or_fetch("k", fetch, ttl=60)
    second = await cache.get_or_fetch("k", fetch, ttl=60)
    assert first == {"ok": 1}
    assert second == {"ok": 1}
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_get_or_fetch_refetches_after_ttl(monkeypatch):
    calls = {"n": 0}
    now = {"t": 1000.0}
    monkeypatch.setattr(cache.time, "monotonic", lambda: now["t"])

    async def fetch():
        calls["n"] += 1
        return calls["n"]

    assert await cache.get_or_fetch("k", fetch, ttl=10) == 1
    now["t"] = 1011.0
    assert await cache.get_or_fetch("k", fetch, ttl=10) == 2
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_clear_resets_entries():
    async def fetch():
        return "v"

    await cache.get_or_fetch("k", fetch, ttl=60)
    cache.clear()
    assert cache.get("k") is None


@pytest.mark.asyncio
async def test_concurrent_get_or_fetch_single_flight():
    started = asyncio.Event()
    release = asyncio.Event()
    calls = {"n": 0}

    async def fetch():
        calls["n"] += 1
        started.set()
        await release.wait()
        return "once"

    task1 = asyncio.create_task(cache.get_or_fetch("k", fetch, ttl=60))
    await started.wait()
    task2 = asyncio.create_task(cache.get_or_fetch("k", fetch, ttl=60))
    await asyncio.sleep(0)
    release.set()
    assert await task1 == "once"
    assert await task2 == "once"
    assert calls["n"] == 1
