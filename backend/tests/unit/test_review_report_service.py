"""ReviewReportService ensure / 规则摘要测试。"""

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.review import ReviewDayResponse, ReviewRunBrief
from app.services.review_report import ReviewReportService, build_rule_summary


def _day_with_runs(trade_date: date = date(2026, 7, 24)) -> ReviewDayResponse:
    return ReviewDayResponse(
        trade_date=trade_date,
        degraded=True,
        missing_sources=["review_events"],
        runs=[
            ReviewRunBrief(
                id=11,
                trade_date=trade_date,
                run_type="overview_analyze",
                status="success",
                source_status={},
                started_at=datetime(2026, 7, 24, 7, 0, tzinfo=timezone.utc),
                finished_at=datetime(2026, 7, 24, 7, 5, tzinfo=timezone.utc),
            )
        ],
        strategy_card={"primary_strategy": "连板接力"},
        candidates=[],
        stage_transitions=[],
    )


def test_build_rule_summary_chinese_fields():
    built = build_rule_summary(_day_with_runs())
    assert "content_json" in built and "content_md" in built
    assert built["content_json"]["primary_strategy"] == "连板接力"
    assert built["content_json"]["candidate_count"] == 0
    assert built["content_json"]["degraded"] is True
    assert "复盘" in built["content_md"]
    assert "连板接力" in built["content_md"]
    assert "供参考，非投资建议" in built["content_md"]


@pytest.mark.asyncio
async def test_ensure_returns_existing_report():
    session = AsyncMock()
    service = ReviewReportService(session)
    service.repo = AsyncMock()
    service.review = AsyncMock()

    existing = SimpleNamespace(
        trade_date=date(2026, 7, 24),
        user_id=None,
        status="rule_fallback",
        content_md="已有摘要",
        content_json={"summary": "已有"},
        model_name=None,
        error=None,
        source_run_ids=[1],
    )
    service.repo.get_report.return_value = existing

    result = await service.ensure(date(2026, 7, 24), user_id=None)

    assert result.status == "rule_fallback"
    assert result.content_md == "已有摘要"
    service.review.get_day.assert_not_called()
    service.repo.upsert_report.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_without_user_writes_rule_fallback():
    session = AsyncMock()
    service = ReviewReportService(session)
    service.repo = AsyncMock()
    service.review = AsyncMock()

    day = _day_with_runs()
    service.repo.get_report.return_value = None
    service.review.get_day.return_value = day
    service.repo.upsert_report.return_value = SimpleNamespace(
        trade_date=day.trade_date,
        user_id=None,
        status="rule_fallback",
        content_md="# rule",
        content_json={"summary": "x", "primary_strategy": "连板接力"},
        model_name=None,
        error=None,
        source_run_ids=[11],
    )

    with patch("app.services.review_report.asyncio.create_task") as create_task:
        result = await service.ensure(day.trade_date, user_id=None)

    assert result.status == "rule_fallback"
    create_task.assert_not_called()
    kwargs = service.repo.upsert_report.await_args.kwargs
    assert kwargs["user_id"] is None
    assert kwargs["status"] == "rule_fallback"
    assert kwargs["content_json"]["primary_strategy"] == "连板接力"
    assert "复盘" in kwargs["content_md"]
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_ensure_with_user_marks_pending_and_schedules():
    session = AsyncMock()
    service = ReviewReportService(session)
    service.repo = AsyncMock()
    service.review = AsyncMock()

    day = _day_with_runs()
    service.repo.get_report.return_value = None
    service.review.get_day.return_value = day
    pending_row = SimpleNamespace(
        trade_date=day.trade_date,
        user_id=7,
        status="pending",
        content_md="",
        content_json={},
        model_name=None,
        error=None,
        source_run_ids=[11],
    )
    service.repo.upsert_report.return_value = pending_row

    mock_task = MagicMock()
    with patch(
        "app.services.review_report.asyncio.create_task", return_value=mock_task
    ) as create_task:
        result = await service.ensure(day.trade_date, user_id=7)

    assert result.status == "pending"
    assert result.user_id == 7
    kwargs = service.repo.upsert_report.await_args.kwargs
    assert kwargs["status"] == "pending"
    assert kwargs["user_id"] == 7
    session.commit.assert_awaited()
    create_task.assert_called_once()
    # 调度的是后台协程，不在 ensure 路径内 await LLM
    coro = create_task.call_args.args[0]
    assert hasattr(coro, "cr_code") or hasattr(coro, "send")
    coro.close()
