"""题材行情多源竞速单元测试。"""

from __future__ import annotations

import asyncio
from datetime import date

import pytest

from app.services.quotes_refresh_race import race_theme_quotes


@pytest.mark.asyncio
async def test_race_commits_only_winner():
    saves: list[list[dict]] = []

    async def slow_collect():
        await asyncio.sleep(0.05)
        return date.today(), [{"code": "BK0001", "name": "慢"}]

    async def fast_collect():
        return date.today(), [{"code": "BK0002", "name": "快"}]

    async def save(themes):
        saves.append(themes)

    result = await race_theme_quotes(
        collectors=[("slow", slow_collect), ("fast", fast_collect)],
        save=save,
    )
    assert result.source == "fast"
    assert result.updated_count == 1
    assert saves == [[{"code": "BK0002", "name": "快"}]]


@pytest.mark.asyncio
async def test_race_cancel_before_save():
    saves: list[list[dict]] = []
    cancel_event = asyncio.Event()

    async def collect():
        # 胜出后、落库前 cancel 已置位 → 不落库
        cancel_event.set()
        return date.today(), [{"code": "BK0001", "name": "x"}]

    async def save(themes):
        saves.append(themes)

    with pytest.raises(asyncio.CancelledError):
        await race_theme_quotes(
            collectors=[("a", collect)],
            save=save,
            cancel_event=cancel_event,
        )
    assert saves == []


@pytest.mark.asyncio
async def test_race_all_fail_raises():
    async def fail_a():
        raise RuntimeError("boom-a")

    async def fail_b():
        return date.today(), []

    async def save(_themes):
        raise AssertionError("save should not be called")

    with pytest.raises(RuntimeError, match="all quote collectors failed"):
        await race_theme_quotes(
            collectors=[("a", fail_a), ("b", fail_b)],
            save=save,
        )


@pytest.mark.asyncio
async def test_race_skips_empty_then_second_wins():
    saves: list[list[dict]] = []

    async def empty_first():
        return date.today(), []

    async def second_ok():
        await asyncio.sleep(0.01)
        return date.today(), [{"code": "BK0009", "name": "第二"}]

    async def save(themes):
        saves.append(themes)

    result = await race_theme_quotes(
        collectors=[("empty", empty_first), ("second", second_ok)],
        save=save,
    )
    assert result.source == "second"
    assert saves == [[{"code": "BK0009", "name": "第二"}]]
