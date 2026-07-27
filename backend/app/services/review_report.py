"""复盘台 AI/规则日报生成服务。"""

from __future__ import annotations

import asyncio
import json
from datetime import date
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.review import ReviewAiReport
from app.repositories.review import ReviewRepository
from app.schemas.review import ReviewAiReportResponse, ReviewDayResponse
from app.services.concept_graph_refresh import model_error_message, parse_model_json
from app.services.model_provider import ModelProviderService
from app.services.review import ReviewService

logger = get_logger(__name__)

SYSTEM_PROMPT = """你是严谨的中国 A 股复盘助手。只能依据用户提供的当日复盘 JSON 摘要撰写日报，不得编造未给出的价格、阶段或新闻。
输出严格 JSON（不要 Markdown 解释），字段：
summary: 一句话中文核心结论
sections: { mainlines, candidates, risks }，每项为中文字符串
markdown: 完整中文 Markdown 正文，须包含「供参考，非投资建议」
证据不足时如实说明，并在 risks 中提示。"""

MIN_REPORT_TIMEOUT_SECONDS = 120
MIN_REPORT_TOKENS = 4_096


def build_rule_summary(day: ReviewDayResponse) -> dict[str, Any]:
    """由日复盘投影生成规则摘要（无 LLM）。"""
    primary: str | None = None
    if isinstance(day.strategy_card, dict):
        raw = day.strategy_card.get("primary_strategy")
        if isinstance(raw, str) and raw.strip():
            primary = raw.strip()

    candidate_count = len(day.candidates)
    stage_up_count = len(day.stage_transitions)
    degraded = bool(day.degraded)

    bits: list[str] = [f"{day.trade_date.isoformat()} 复盘"]
    if primary:
        bits.append(f"主策略「{primary}」")
    bits.append(f"候选 {candidate_count} 只")
    bits.append(f"阶段迁移 {stage_up_count} 次")
    if degraded:
        bits.append("数据已降级")
    summary = "；".join(bits) + "。"

    lines: list[str] = [
        f"# {day.trade_date.isoformat()} 复盘规则摘要",
        "",
        summary,
        "",
    ]
    if primary:
        lines.append(f"**主策略**：{primary}")
    else:
        lines.append("**主策略**：暂无")
    lines.append(f"**候选数量**：{candidate_count}")
    lines.append(f"**阶段上移/迁移**：{stage_up_count}")
    if day.candidates:
        lines.append("")
        lines.append("## 候选")
        for c in day.candidates[:8]:
            name = c.stock_name or c.stock_code or f"#{c.stock_id}"
            lines.append(f"- {name}（{c.strategy or '—'}，分 {c.score}）")
    if day.stage_transitions:
        lines.append("")
        lines.append("## 阶段迁移")
        for t in day.stage_transitions[:8]:
            name = t.theme_name or f"题材#{t.theme_id}"
            lines.append(f"- {name}：{t.from_stage or '—'} → {t.to_stage}")
    if degraded and day.missing_sources:
        lines.append("")
        lines.append(f"**缺失数据源**：{', '.join(day.missing_sources)}")
    lines.extend(["", "供参考，非投资建议。"])

    content_json: dict[str, Any] = {
        "summary": summary,
        "primary_strategy": primary,
        "candidate_count": candidate_count,
        "stage_up_count": stage_up_count,
        "degraded": degraded,
    }
    return {"content_json": content_json, "content_md": "\n".join(lines)}


def _to_response(row: ReviewAiReport) -> ReviewAiReportResponse:
    return ReviewAiReportResponse(
        trade_date=row.trade_date,
        user_id=row.user_id,
        status=row.status,
        content_md=row.content_md or "",
        content_json=dict(row.content_json or {}),
        model_name=row.model_name,
        error=row.error,
        source_run_ids=list(row.source_run_ids or []),
    )


def _source_run_ids(day: ReviewDayResponse) -> list[Any]:
    return [r.id for r in day.runs]


def _day_prompt_payload(day: ReviewDayResponse) -> dict[str, Any]:
    return {
        "trade_date": day.trade_date.isoformat(),
        "degraded": day.degraded,
        "missing_sources": day.missing_sources,
        "strategy_card": day.strategy_card,
        "candidates": [c.model_dump() for c in day.candidates],
        "stage_transitions": [t.model_dump(mode="json") for t in day.stage_transitions],
        "performance": day.performance.model_dump() if day.performance else None,
        "run_ids": _source_run_ids(day),
    }


def _normalize_llm_content(parsed: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    summary = parsed.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("缺少 summary")
    sections = parsed.get("sections")
    if not isinstance(sections, dict):
        raise ValueError("缺少 sections")
    for key in ("mainlines", "candidates", "risks"):
        if key not in sections:
            raise ValueError(f"sections 缺少 {key}")
    markdown = parsed.get("markdown")
    if not isinstance(markdown, str) or not markdown.strip():
        raise ValueError("缺少 markdown")
    content_json = {
        "summary": summary.strip(),
        "sections": {
            "mainlines": str(sections.get("mainlines") or ""),
            "candidates": str(sections.get("candidates") or ""),
            "risks": str(sections.get("risks") or ""),
        },
        "markdown": markdown.strip(),
    }
    return markdown.strip(), content_json


class ReviewReportService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        repo: ReviewRepository | None = None,
        review: ReviewService | None = None,
    ):
        self.session = session
        self.repo = repo or ReviewRepository(session)
        self.review = review or ReviewService(session)

    async def get_report(
        self, trade_date: date, user_id: int | None
    ) -> ReviewAiReportResponse | None:
        row = await self.repo.get_report(trade_date, user_id)
        if row is None:
            return None
        return _to_response(row)

    async def ensure(
        self, trade_date: date, user_id: int | None
    ) -> ReviewAiReportResponse:
        existing = await self.repo.get_report(trade_date, user_id)
        if existing is not None and existing.status in ("success", "rule_fallback"):
            return _to_response(existing)

        day = await self.review.get_day(trade_date)
        if user_id is None:
            return await self._save_rule(day, user_id=None)

        row = await self.repo.upsert_report(
            trade_date=day.trade_date,
            user_id=user_id,
            status="pending",
            content_md="",
            content_json={},
            model_name=None,
            error=None,
            source_run_ids=_source_run_ids(day),
        )
        await self.session.commit()
        asyncio.create_task(_generate_in_background(day.trade_date, user_id))
        return _to_response(row)

    async def _save_rule(
        self,
        day: ReviewDayResponse,
        *,
        user_id: int | None,
        error: str | None = None,
        model_name: str | None = None,
    ) -> ReviewAiReportResponse:
        built = build_rule_summary(day)
        row = await self.repo.upsert_report(
            trade_date=day.trade_date,
            user_id=user_id,
            status="rule_fallback",
            content_md=built["content_md"],
            content_json=built["content_json"],
            model_name=model_name,
            error=error,
            source_run_ids=_source_run_ids(day),
        )
        await self.session.commit()
        return _to_response(row)


async def _generate_in_background(trade_date: date, user_id: int) -> None:
    async with AsyncSessionLocal() as session:
        service = ReviewReportService(session)
        try:
            day = await service.review.get_day(trade_date)
            await service.repo.upsert_report(
                trade_date=day.trade_date,
                user_id=user_id,
                status="running",
                content_md="",
                content_json={},
                model_name=None,
                error=None,
                source_run_ids=_source_run_ids(day),
            )
            await session.commit()

            providers = ModelProviderService(session, user_id)
            provider = await providers.get_default()
            adapter = providers.adapter(provider)
            if adapter.max_tokens < MIN_REPORT_TOKENS:
                adapter.max_tokens = MIN_REPORT_TOKENS
            timeout = max(
                int(provider.timeout_seconds or 60), MIN_REPORT_TIMEOUT_SECONDS
            )
            user_prompt = (
                "请基于下列当日复盘 JSON 摘要输出日报 JSON。\n\n"
                + json.dumps(_day_prompt_payload(day), ensure_ascii=False, default=str)
            )
            raw = await adapter.complete(
                SYSTEM_PROMPT,
                user_prompt,
                json_mode=True,
                reasoning=False,
                timeout_seconds=timeout,
            )
            content_md, content_json = _normalize_llm_content(parse_model_json(raw))
            await service.repo.upsert_report(
                trade_date=day.trade_date,
                user_id=user_id,
                status="success",
                content_md=content_md,
                content_json=content_json,
                model_name=provider.model,
                error=None,
                source_run_ids=_source_run_ids(day),
            )
        except Exception as exc:  # noqa: BLE001 — 后台不得抛穿事件循环
            logger.warning(
                "review_report_generate_failed",
                trade_date=str(trade_date),
                user_id=user_id,
                error=str(exc),
            )
            try:
                await session.rollback()
            except Exception:  # noqa: BLE001
                pass
            try:
                day = await ReviewService(session).get_day(trade_date)
                err = (
                    model_error_message(exc)
                    if isinstance(exc, (httpx.HTTPError, KeyError, ValueError))
                    else str(exc)[:300]
                )
                if isinstance(exc, HTTPException):
                    err = str(exc.detail)[:300]
                built = build_rule_summary(day)
                await ReviewRepository(session).upsert_report(
                    trade_date=day.trade_date,
                    user_id=user_id,
                    status="rule_fallback",
                    content_md=built["content_md"],
                    content_json=built["content_json"],
                    model_name=None,
                    error=err,
                    source_run_ids=_source_run_ids(day),
                )
            except Exception as fallback_exc:  # noqa: BLE001
                logger.warning(
                    "review_report_fallback_failed",
                    trade_date=str(trade_date),
                    user_id=user_id,
                    error=str(fallback_exc),
                )
        finally:
            try:
                await session.commit()
            except Exception as commit_exc:  # noqa: BLE001
                logger.warning(
                    "review_report_commit_failed",
                    trade_date=str(trade_date),
                    error=str(commit_exc),
                )
