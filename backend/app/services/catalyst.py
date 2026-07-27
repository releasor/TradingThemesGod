"""催化雷达聚合服务。"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.short_term_signal import SectorRotationSnapshot
from app.models.theme import Theme
from app.models.theme_driver_event import ThemeDriverEvent
from app.repositories.catalyst import CatalystRepository, FeedRow
from app.schemas.catalyst import (
    CatalystEnsureResponse,
    CatalystFeedItem,
    CatalystFeedResponse,
    CatalystThemeSummaryResponse,
    NewsHeadlineItem,
)
from app.services.catalyst_rules import ClassifyResult
from app.services.concept_graph_refresh import parse_model_json
from app.services.model_provider import ModelProviderService

logger = get_logger(__name__)

SUMMARY_DAYS = 7
MODEL_RECLASSIFY_TIMEOUT_SECONDS = 60

SYSTEM_PROMPT = """你是严谨的中国 A 股催化事件分类助手。只能依据用户提供的事件标题、摘要与来源判断分类，不得编造未给出的信息。
输出严格 JSON（不要 Markdown 解释），字段：
freshness: new / replay / unknown 之一
actor_type: policy / company / other / unknown 之一
confidence: 0-100 整数
rationale: 一句中文理由"""

_VALID_FRESHNESS = frozenset({"new", "replay", "unknown"})
_VALID_ACTOR = frozenset({"policy", "company", "other", "unknown"})


def _feed_row_to_item(row: FeedRow) -> CatalystFeedItem:
    return CatalystFeedItem(
        event_id=row.event_id,
        theme_id=row.theme_id,
        theme_name=row.theme_name,
        title=row.title,
        summary=row.summary,
        source=row.source,
        url=row.url,
        published_at=row.published_at,
        relevance_score=row.relevance_score,
        freshness=row.freshness,
        actor_type=row.actor_type,
        classified_by=row.classified_by,
    )


def _event_to_feed_item(event: ThemeDriverEvent, *, theme_name: str) -> CatalystFeedItem:
    return CatalystFeedItem(
        event_id=event.id,
        theme_id=event.theme_id,
        theme_name=theme_name,
        title=event.title,
        summary=event.summary,
        source=event.source,
        url=event.url,
        published_at=event.published_at,
        relevance_score=event.relevance_score,
        freshness=event.freshness,
        actor_type=event.actor_type,
        classified_by=event.classified_by,
    )


def _normalize_model_result(parsed: dict) -> ClassifyResult:
    freshness = parsed.get("freshness")
    if not isinstance(freshness, str) or freshness not in _VALID_FRESHNESS:
        freshness = "unknown"
    actor_type = parsed.get("actor_type")
    if not isinstance(actor_type, str) or actor_type not in _VALID_ACTOR:
        actor_type = "unknown"
    confidence_raw = parsed.get("confidence")
    confidence = int(confidence_raw) if isinstance(confidence_raw, (int, float)) else 50
    confidence = max(0, min(100, confidence))
    rationale = parsed.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        rationale = "模型分类"
    return ClassifyResult(
        freshness=freshness,
        actor_type=actor_type,
        confidence=confidence,
        rationale=rationale.strip(),
    )


def _event_prompt_payload(event: ThemeDriverEvent) -> dict:
    return {
        "title": event.title,
        "summary": event.summary,
        "source": event.source,
        "published_at": event.published_at.isoformat(),
        "current_freshness": event.freshness,
        "current_actor_type": event.actor_type,
    }


class CatalystService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        repo: CatalystRepository | None = None,
    ):
        self.session = session
        self.repo = repo or CatalystRepository(session)

    async def get_feed(
        self,
        *,
        freshness: str | None = None,
        actor_type: str | None = None,
        theme_id: int | None = None,
        q: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 30,
        offset: int = 0,
        include_total: bool = True,
    ) -> CatalystFeedResponse:
        rows = await self.repo.list_feed(
            freshness=freshness,
            actor_type=actor_type,
            theme_id=theme_id,
            q=q,
            start=start,
            end=end,
            limit=limit,
            offset=offset,
        )
        total: int | None = None
        if include_total:
            total = await self.repo.count_feed(
                freshness=freshness,
                actor_type=actor_type,
                theme_id=theme_id,
                q=q,
                start=start,
                end=end,
            )
        return CatalystFeedResponse(
            items=[_feed_row_to_item(row) for row in rows],
            total=total,
        )

    async def get_theme_summary(self, theme_id: int) -> CatalystThemeSummaryResponse:
        theme = await self.session.get(Theme, theme_id)
        if theme is None or theme.deleted_at is not None:
            raise HTTPException(404, "题材不存在")

        snapshot = await self.session.scalar(
            select(SectorRotationSnapshot)
            .where(SectorRotationSnapshot.theme_id == theme_id)
            .order_by(desc(SectorRotationSnapshot.trade_date))
            .limit(1)
        )

        since = datetime.now(UTC) - timedelta(days=SUMMARY_DAYS)
        counts = await self.repo.count_by_theme(theme_id, since)
        events = await self.repo.list_theme_events(theme_id, limit=10)
        articles = await self.repo.list_news_headlines_for_theme(theme.name, limit=8)

        return CatalystThemeSummaryResponse(
            theme_id=theme.id,
            theme_name=theme.name,
            lifecycle_stage=snapshot.lifecycle_stage if snapshot else None,
            strength_score=snapshot.strength_score if snapshot else None,
            counts=counts,
            recent_events=[
                _event_to_feed_item(event, theme_name=theme.name) for event in events
            ],
            news_headlines=[
                NewsHeadlineItem(
                    title=article.title,
                    url=article.url,
                    published_at=article.published_at,
                    match_note="关键词匹配",
                )
                for article in articles
            ],
        )

    async def ensure_classify(
        self,
        *,
        days: int = 7,
        use_model: bool = False,
        user_id: int | None = None,
    ) -> CatalystEnsureResponse:
        classified_rules = await self.repo.classify_recent(days=days)
        await self.session.commit()

        model_queued = False
        if use_model and user_id is not None:
            asyncio.create_task(_reclassify_in_background(days=days, user_id=user_id))
            model_queued = True

        return CatalystEnsureResponse(
            classified_rules=classified_rules,
            model_queued=model_queued,
        )


async def _load_events_for_model(session: AsyncSession, days: int) -> list[ThemeDriverEvent]:
    since = datetime.now(UTC) - timedelta(days=days)
    result = await session.scalars(
        select(ThemeDriverEvent)
        .where(
            ThemeDriverEvent.published_at >= since,
            or_(
                ThemeDriverEvent.freshness == "unknown",
                ThemeDriverEvent.classified_by == "rules",
            ),
        )
        .order_by(ThemeDriverEvent.published_at)
    )
    return list(result.all())


async def _reclassify_in_background(*, days: int, user_id: int) -> None:
    async with AsyncSessionLocal() as session:
        repo = CatalystRepository(session)
        try:
            events = await _load_events_for_model(session, days)
            if not events:
                return

            providers = ModelProviderService(session, user_id)
            provider = await providers.get_default()
            adapter = providers.adapter(provider)
            model_name = provider.model

            for event in events:
                try:
                    user_prompt = (
                        "请对下列催化事件输出分类 JSON。\n\n"
                        + json.dumps(_event_prompt_payload(event), ensure_ascii=False)
                    )
                    raw = await adapter.complete(
                        SYSTEM_PROMPT,
                        user_prompt,
                        json_mode=True,
                        reasoning=False,
                        timeout_seconds=MODEL_RECLASSIFY_TIMEOUT_SECONDS,
                    )
                    result = _normalize_model_result(parse_model_json(raw))
                    await repo.apply_classification(
                        event.id,
                        result,
                        method="model",
                        model_name=model_name,
                    )
                except Exception as exc:  # noqa: BLE001 — 单条失败保留规则标签
                    logger.warning(
                        "catalyst_model_reclassify_event_failed",
                        event_id=event.id,
                        user_id=user_id,
                        error=str(exc)[:300],
                    )
        except Exception as exc:  # noqa: BLE001 — 无默认模型等整体失败
            logger.warning(
                "catalyst_model_reclassify_failed",
                user_id=user_id,
                error=str(exc)[:300],
            )
        finally:
            try:
                await session.commit()
            except Exception as commit_exc:  # noqa: BLE001
                logger.warning(
                    "catalyst_model_reclassify_commit_failed",
                    user_id=user_id,
                    error=str(commit_exc),
                )
