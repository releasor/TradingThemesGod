"""prompt_optimize 单元测试。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas.prompt_workbench import (
    DesignRequest,
    DualTestRequest,
    IterateRequest,
    OptimizeRequest,
)
from app.services.prompt_optimize import PromptOptimizeService


@pytest.mark.asyncio
async def test_optimize_rejects_unknown_framework():
    session = AsyncMock()
    svc = PromptOptimizeService(session, user_id=1)
    with pytest.raises(HTTPException) as exc:
        await svc.optimize(
            OptimizeRequest(
                source="写一篇文章",
                mode="framework",
                framework="NOPE",
                persist=False,
            )
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_optimize_smart_returns_result():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    svc = PromptOptimizeService(session, user_id=1)
    with patch.object(
        svc.llm, "run_completion", new=AsyncMock(return_value="优化后的内容")
    ):
        result = await svc.optimize(
            OptimizeRequest(source="原始", mode="smart", persist=False)
        )
    assert result.result == "优化后的内容"
    assert result.run_id is None


@pytest.mark.asyncio
async def test_design_calls_llm():
    session = AsyncMock()
    svc = PromptOptimizeService(session, user_id=1)
    with patch.object(
        svc.llm, "run_completion", new=AsyncMock(return_value="设计结果")
    ) as mock_run:
        result = await svc.design(DesignRequest(goal="写周报"))
    assert result.result == "设计结果"
    mock_run.assert_awaited_once()


@pytest.mark.asyncio
async def test_dual_test_calls_twice():
    session = AsyncMock()
    svc = PromptOptimizeService(session, user_id=1)
    with patch.object(
        svc.llm,
        "run_completion",
        new=AsyncMock(side_effect=["A出", "B出"]),
    ) as mock_run:
        result = await svc.dual_test(
            DualTestRequest(
                prompt_a="pa",
                prompt_b="pb",
                user_message="你好",
            )
        )
    assert result.output_a == "A出"
    assert result.output_b == "B出"
    assert mock_run.await_count == 2


@pytest.mark.asyncio
async def test_optimize_stream_yields_deltas_then_done():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    async def fake_stream(*_a, **_k):
        yield "你好"
        yield "世界"

    svc = PromptOptimizeService(session, user_id=1)
    with patch.object(svc.llm, "stream_completion", new=fake_stream):
        events = [
            e
            async for e in svc.optimize_stream(
                OptimizeRequest(source="原始", mode="smart", persist=False)
            )
        ]
    assert events[0] == {"type": "start"}
    assert events[1] == {"type": "delta", "text": "你好"}
    assert events[2] == {"type": "delta", "text": "世界"}
    assert events[3]["type"] == "done"
    assert events[3]["result"] == "你好世界"
    assert events[3]["run_id"] is None


@pytest.mark.asyncio
async def test_iterate_stream_yields_done():
    session = AsyncMock()

    async def fake_stream(*_a, **_k):
        yield "改好了"

    svc = PromptOptimizeService(session, user_id=1)
    with patch.object(svc.llm, "stream_completion", new=fake_stream):
        events = [
            e
            async for e in svc.iterate_stream(
                IterateRequest(current="当前", instruction="更短", run_id=None)
            )
        ]
    assert events[0] == {"type": "start"}
    assert events[1] == {"type": "delta", "text": "改好了"}
    assert events[2] == {"type": "done", "result": "改好了", "run_id": None}

@pytest.mark.asyncio
async def test_design_stream_yields_deltas_then_done():
    session = AsyncMock()

    async def fake_stream(*_a, **_k):
        yield "设"
        yield "计稿"

    svc = PromptOptimizeService(session, user_id=1)
    with patch.object(svc.llm, "stream_completion", new=fake_stream):
        events = [
            e
            async for e in svc.design_stream(
                DesignRequest(goal="写周报", notes="简洁")
            )
        ]
    assert events[0] == {"type": "start"}
    assert events[1] == {"type": "delta", "text": "设"}
    assert events[2] == {"type": "delta", "text": "计稿"}
    assert events[3] == {"type": "done", "result": "设计稿", "run_id": None}


@pytest.mark.asyncio
async def test_list_runs_returns_summaries():
    session = AsyncMock()
    run = MagicMock()
    run.id = 7
    run.source = "src"
    run.result = "out"
    run.mode = "smart"
    run.framework = None
    run.extra_goal = None
    run.versions = [{"result": "out"}]
    run.created_at = "2026-01-01T00:00:00"
    run.updated_at = "2026-01-02T00:00:00"
    run.user_id = 1

    scalars = MagicMock()
    scalars.all.return_value = [run]
    session.scalars = AsyncMock(return_value=scalars)

    svc = PromptOptimizeService(session, user_id=1)
    rows = await svc.list_runs(limit=10)
    assert len(rows) == 1
    assert rows[0].id == 7
    assert rows[0].version_count == 1
    assert rows[0].result == "out"

