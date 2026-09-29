"""设计 / 优化 / 双测服务。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt_workbench import PromptOptimizeRun
from app.schemas.prompt_workbench import (
    DesignRequest,
    DualTestRequest,
    DualTestResult,
    IterateRequest,
    OptimizeRequest,
    OptimizeRunResponse,
    OptimizeRunSummary,
    TextResult,
)
from sqlalchemy import select
from app.services.prompt_llm import PromptLLMService
from app.services.prompt_templates import (
    FRAMEWORKS,
    build_design_system,
    build_design_user,
    build_iterate_system,
    build_iterate_user,
    build_optimize_system,
    build_optimize_user,
)




_EMPTY_STREAM_RESULT_MSG = "模型返回了空内容，请更换模型或重试"


def _require_stream_result(result: str) -> str:
    cleaned = result.strip()
    if not cleaned:
        raise HTTPException(502, _EMPTY_STREAM_RESULT_MSG)
    return cleaned


class PromptOptimizeService:
    def __init__(self, session: AsyncSession, user_id: int):
        self.session = session
        self.user_id = user_id
        self.llm = PromptLLMService(session, user_id)

    def _normalize_framework(self, payload: OptimizeRequest) -> str | None:
        framework = payload.framework
        if payload.mode == "framework":
            if not framework or framework.upper() not in FRAMEWORKS:
                raise HTTPException(
                    400,
                    f"不支持的框架，可选：{', '.join(FRAMEWORKS)}",
                )
            return framework.upper()
        return None

    async def design(self, payload: DesignRequest) -> TextResult:
        result = await self.llm.run_completion(
            build_design_system(),
            build_design_user(payload.goal, payload.notes),
            provider_id=payload.provider_id,
        )
        return TextResult(result=result.strip(), run_id=None)

    async def design_stream(
        self, payload: DesignRequest
    ) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "start"}
        parts: list[str] = []
        status_sent = False
        async for delta in self.llm.stream_completion(
            build_design_system(),
            build_design_user(payload.goal, payload.notes),
            provider_id=payload.provider_id,
        ):
            if not delta:
                if not status_sent:
                    status_sent = True
                    yield {"type": "status", "message": "模型思考中，正文即将开始…"}
                continue
            parts.append(delta)
            yield {"type": "delta", "text": delta}
        result = _require_stream_result("".join(parts))
        yield {"type": "done", "result": result, "run_id": None}

    async def optimize(self, payload: OptimizeRequest) -> TextResult:
        framework = self._normalize_framework(payload)
        result = await self.llm.run_completion(
            build_optimize_system(
                mode=payload.mode,
                framework=framework,
                extra_goal=payload.extra_goal,
            ),
            build_optimize_user(payload.source),
            provider_id=payload.provider_id,
        )
        result = result.strip()
        run_id = await self._persist_optimize(payload, framework, result)
        return TextResult(result=result, run_id=run_id)

    async def optimize_stream(
        self, payload: OptimizeRequest
    ) -> AsyncIterator[dict[str, Any]]:
        framework = self._normalize_framework(payload)
        # 立刻通知前端已接通，避免首 token 前右侧长时间空白
        yield {"type": "start"}
        parts: list[str] = []
        status_sent = False
        async for delta in self.llm.stream_completion(
            build_optimize_system(
                mode=payload.mode,
                framework=framework,
                extra_goal=payload.extra_goal,
            ),
            build_optimize_user(payload.source),
            provider_id=payload.provider_id,
        ):
            if not delta:
                if not status_sent:
                    status_sent = True
                    yield {"type": "status", "message": "模型思考中，正文即将开始…"}
                continue
            parts.append(delta)
            yield {"type": "delta", "text": delta}
        result = _require_stream_result("".join(parts))
        yield {"type": "done", "result": result, "run_id": None}
        run_id = await self._persist_optimize(payload, framework, result)
        if run_id is not None:
            yield {"type": "persisted", "run_id": run_id}

    async def _persist_optimize(
        self, payload: OptimizeRequest, framework: str | None, result: str
    ) -> int | None:
        if not payload.persist:
            return None
        run = PromptOptimizeRun(
            user_id=self.user_id,
            source=payload.source,
            result=result,
            mode=payload.mode,
            framework=framework,
            extra_goal=payload.extra_goal,
            versions=[{"result": result}],
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run.id

    async def iterate(self, payload: IterateRequest) -> TextResult:
        result = await self.llm.run_completion(
            build_iterate_system(),
            build_iterate_user(payload.current, payload.instruction),
            provider_id=payload.provider_id,
        )
        result = result.strip()
        run_id = await self._persist_iterate(payload, result)
        return TextResult(result=result, run_id=run_id)

    async def iterate_stream(
        self, payload: IterateRequest
    ) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "start"}
        parts: list[str] = []
        status_sent = False
        async for delta in self.llm.stream_completion(
            build_iterate_system(),
            build_iterate_user(payload.current, payload.instruction),
            provider_id=payload.provider_id,
        ):
            if not delta:
                if not status_sent:
                    status_sent = True
                    yield {"type": "status", "message": "模型思考中，正文即将开始…"}
                continue
            parts.append(delta)
            yield {"type": "delta", "text": delta}
        result = _require_stream_result("".join(parts))
        yield {"type": "done", "result": result, "run_id": payload.run_id}
        run_id = await self._persist_iterate(payload, result)
        if run_id is not None:
            yield {"type": "persisted", "run_id": run_id}

    async def _persist_iterate(self, payload: IterateRequest, result: str) -> int | None:
        run_id = payload.run_id
        if run_id is None:
            return None
        run = await self.session.get(PromptOptimizeRun, run_id)
        if run is None or run.user_id != self.user_id:
            raise HTTPException(404, "优化记录不存在")
        versions = list(run.versions or [])
        versions.append({"result": result, "instruction": payload.instruction})
        run.result = result
        run.versions = versions
        await self.session.commit()
        return run_id

    async def dual_test(self, payload: DualTestRequest) -> DualTestResult:
        output_a = await self.llm.run_completion(
            payload.prompt_a,
            payload.user_message,
            provider_id=payload.provider_id,
        )
        output_b = await self.llm.run_completion(
            payload.prompt_b,
            payload.user_message,
            provider_id=payload.provider_id,
        )
        return DualTestResult(
            output_a=output_a.strip(),
            output_b=output_b.strip(),
        )

    async def get_run(self, run_id: int) -> OptimizeRunResponse:
        run = await self.session.get(PromptOptimizeRun, run_id)
        if run is None or run.user_id != self.user_id:
            raise HTTPException(404, "优化记录不存在")
        return OptimizeRunResponse.model_validate(run)

    async def list_runs(self, *, limit: int = 20) -> list[OptimizeRunSummary]:
        limit = max(1, min(limit, 50))
        rows = (
            await self.session.scalars(
                select(PromptOptimizeRun)
                .where(PromptOptimizeRun.user_id == self.user_id)
                .order_by(PromptOptimizeRun.updated_at.desc())
                .limit(limit)
            )
        ).all()
        out: list[OptimizeRunSummary] = []
        for run in rows:
            versions = list(run.versions or [])
            out.append(
                OptimizeRunSummary(
                    id=run.id,
                    source=run.source,
                    result=run.result,
                    mode=run.mode,
                    framework=run.framework,
                    extra_goal=run.extra_goal,
                    version_count=max(len(versions), 1),
                    created_at=run.created_at,
                    updated_at=run.updated_at,
                )
            )
        return out
