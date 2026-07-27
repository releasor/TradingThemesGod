"""ReviewEventWriter 单元测试。"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock

import pytest

from app.services.review_events import ReviewEventWriter


@pytest.mark.asyncio
async def test_writer_records_strategy_card_event():
    repo = AsyncMock()
    run = SimpleNamespace(id=1, trade_date=date(2026, 7, 24))
    repo.create_run.return_value = run
    writer = ReviewEventWriter(repo)

    async with writer.track(trade_date=date(2026, 7, 24), run_type="overview_analyze") as ctx:
        await ctx.emit_strategy_card({"title": "指数情绪策略卡", "primary_strategy": "连板接力"})

    repo.add_event.assert_awaited()
    kwargs = repo.add_event.await_args.kwargs
    assert kwargs["event_type"] == "strategy_card"
    assert kwargs["entity_type"] == "market"
    repo.finish_run.assert_awaited_with(1, status="success", source_status=ANY, error=None)


@pytest.mark.asyncio
async def test_writer_marks_failed_on_exception():
    repo = AsyncMock()
    repo.create_run.return_value = SimpleNamespace(id=9, trade_date=date(2026, 7, 24))
    writer = ReviewEventWriter(repo)

    with pytest.raises(RuntimeError):
        async with writer.track(trade_date=date(2026, 7, 24), run_type="signals_refresh") as ctx:
            raise RuntimeError("boom")

    repo.finish_run.assert_awaited()
    assert repo.finish_run.await_args.kwargs["status"] == "failed"
    assert repo.finish_run.await_args.kwargs["error"] == "boom"


@pytest.mark.asyncio
async def test_set_partial_finishes_as_partial():
    repo = AsyncMock()
    repo.create_run.return_value = SimpleNamespace(id=3, trade_date=date(2026, 7, 24))
    writer = ReviewEventWriter(repo)

    async with writer.track(trade_date=date(2026, 7, 24), run_type="signals_refresh") as ctx:
        ctx.set_partial({"signals": {"missing": ["dragon_tiger"]}})

    repo.finish_run.assert_awaited_with(
        3,
        status="partial",
        source_status={"signals": {"missing": ["dragon_tiger"]}},
        error=None,
    )
