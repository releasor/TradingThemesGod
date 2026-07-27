"""互联网资料驱动的题材档案和事件增量刷新。"""

import asyncio
import json
import time
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.theme_insights import deduplicate_event_rows
from app.models.stock import Stock
from app.models.theme import Theme
from app.models.theme_stock import ThemeStock
from app.core.logging import get_logger
from app.repositories.catalyst import CatalystRepository
from app.repositories.news import NewsRepository
from app.repositories.theme_insight import ThemeInsightRepository
from app.schemas.theme_insight import (
    ExtractedThemeInsights,
    ThemeInsightRefreshResponse,
)
from app.services.concept_graph_refresh import parse_model_json
from app.services.model_provider import ModelProviderService
from app.services.web_research import ResearchSource, WebResearchService

SYSTEM_PROMPT = """你是严谨的中国 A 股题材研究员。只能依据输入来源生成 JSON，不得补充未提供的事实或 URL。返回 profile 和 events；事件 relevance_score 为 0 到 100。"""

logger = get_logger(__name__)


class ThemeInsightRefreshService:
    def __init__(
        self,
        session: AsyncSession,
        research: WebResearchService | None = None,
        providers: ModelProviderService | None = None,
        news: NewsRepository | None = None,
        insights: ThemeInsightRepository | None = None,
        catalyst: CatalystRepository | None = None,
    ):
        self.session = session
        self.research = research or WebResearchService()
        self.providers = providers
        self.news = news or NewsRepository(session)
        self.insights = insights or ThemeInsightRepository(session)
        self.catalyst = catalyst or CatalystRepository(session)

    async def _theme_context(self, theme_id: int) -> tuple[Theme, list[Stock]]:
        theme = await self.session.get(Theme, theme_id)
        if theme is None or theme.deleted_at is not None:
            raise HTTPException(404, "题材不存在")
        result = await self.session.execute(
            select(Stock)
            .join(ThemeStock, ThemeStock.stock_id == Stock.id)
            .where(ThemeStock.theme_id == theme_id)
            .order_by(ThemeStock.sort_order)
            .limit(10)
        )
        return theme, list(result.scalars().all())

    @staticmethod
    def _prompt(theme: Theme, sources: list[ResearchSource]) -> str:
        payload = [
            {
                "title": source.title,
                "url": source.url,
                "publisher": source.publisher,
                "text": source.text[:2000],
            }
            for source in sources
        ]
        return f"题材：{theme.name}\n已有描述：{theme.description or '无'}\n来源：{json.dumps(payload, ensure_ascii=False)}"

    async def _extract(
        self, theme: Theme, sources: list[ResearchSource]
    ) -> tuple[ExtractedThemeInsights, dict[str, str | None]]:
        debug: dict[str, str | None] = {
            "model_name": None,
            "model_error": None,
            "model_reasoning": None,
            "model_raw_response": None,
        }
        if self.providers is None:
            raise HTTPException(409, "请先在模型设置中配置并启用默认模型")
        provider = await self.providers.get_default()
        debug["model_name"] = getattr(provider, "model", None) or getattr(
            provider, "name", None
        )
        # 开启 reasoning，便于把厂商返回的思考过程带回前端排障
        result = await self.providers.adapter(provider).complete_detailed(
            SYSTEM_PROMPT, self._prompt(theme, sources), reasoning=True
        )
        debug["model_reasoning"] = result.reasoning
        debug["model_raw_response"] = result.raw_preview or result.content[:12000]
        extracted = ExtractedThemeInsights.model_validate(parse_model_json(result.content))
        allowed = {source.url for source in sources}
        if extracted.profile and any(
            url not in allowed for url in extracted.profile.source_urls
        ):
            raise ValueError("题材档案引用了未抓取的来源")
        extracted.events = [
            event
            for event in extracted.events
            if event.source_url in allowed and event.relevance_score >= 60
        ]
        return extracted, debug

    async def refresh(
        self, theme_id: int, *, refresh_profile: bool = True
    ) -> ThemeInsightRefreshResponse:
        started = time.monotonic()
        theme, stocks = await self._theme_context(theme_id)
        reset_failures = getattr(self.research, "reset_failures", None)
        if callable(reset_failures):
            reset_failures()
        profile_research = (
            self.research.research_profile(theme.name)
            if refresh_profile
            else asyncio.sleep(0, result=[])
        )
        profile_sources, event_sources, news_items = await asyncio.gather(
            profile_research,
            self.research.research_driver_events(
                theme.name, [stock.name for stock in stocks]
            ),
            self.news.list_theme_candidates(
                [theme.name, *[stock.name for stock in stocks]],
                datetime.now(UTC) - timedelta(days=30),
            ),
        )
        news_sources = [
            ResearchSource(
                title=item.title,
                url=item.url,
                text=item.summary or item.title,
                publisher=item.source,
                published_at=item.published_at,
            )
            for item in news_items
        ]
        sources = list(
            {
                source.url: source
                for source in [*profile_sources, *event_sources, *news_sources]
            }.values()
        )
        if not sources:
            raise HTTPException(502, "未抓取到可验证的题材资料，原数据已保留")
        degraded = False
        model_debug: dict[str, str | None] = {
            "model_name": None,
            "model_error": None,
            "model_reasoning": None,
            "model_raw_response": None,
        }
        try:
            extracted, model_debug = await self._extract(theme, sources)
        except (
            httpx.HTTPError,
            HTTPException,
            KeyError,
            TypeError,
            ValidationError,
            ValueError,
        ) as exc:
            extracted = ExtractedThemeInsights()
            degraded = True
            detail = getattr(exc, "detail", None)
            model_debug["model_error"] = (
                detail if isinstance(detail, str) else str(exc)
            )[:4000]
            # HTTPException(409) 等也可能在 get_default 时抛出，补模型名
            if model_debug["model_name"] is None and self.providers is not None:
                try:
                    provider = await self.providers.get_default()
                    model_debug["model_name"] = getattr(provider, "model", None)
                except Exception:
                    pass

        now = datetime.now(UTC)
        source_map = {source.url: source for source in sources}
        profile_updated = refresh_profile and extracted.profile is not None
        if refresh_profile and extracted.profile:
            await self.insights.upsert_profile(
                theme.id,
                extracted.profile,
                [
                    {
                        "title": source_map[url].title,
                        "url": url,
                        "publisher": source_map[url].publisher,
                        "published_at": source_map[url].published_at,
                    }
                    for url in extracted.profile.source_urls
                ],
                now,
            )
        if degraded:
            subject_words = [theme.name, *[stock.name for stock in stocks]]
            driver_words = ("政策", "订单", "发布", "突破", "涨价", "扩产", "业绩")
            event_rows = []
            for source in sources:
                text = f"{source.title} {source.text}"
                if any(word in text for word in subject_words) and any(
                    word in text for word in driver_words
                ):
                    event_rows.append(
                        {
                            "title": source.title[:500],
                            "summary": source.text[:500],
                            "source": source.publisher or "公开网页",
                            "url": source.url,
                            "published_at": source.published_at or now,
                            "relevance_score": 40,
                            "crawled_at": now,
                        }
                    )
        else:
            event_rows = [
                {
                    "title": event.title,
                    "summary": event.summary,
                    "source": source_map[event.source_url].publisher or "公开网页",
                    "url": event.source_url,
                    "published_at": event.published_at,
                    "relevance_score": event.relevance_score,
                    "crawled_at": now,
                }
                for event in extracted.events
            ]
        event_rows = deduplicate_event_rows(event_rows)
        inserted, updated = await self.insights.upsert_events(theme.id, event_rows)
        if event_rows:
            try:
                event_ids = await self.catalyst.resolve_event_ids(theme.id, event_rows)
                if event_ids:
                    await self.catalyst.classify_event_ids(event_ids)
            except Exception:
                logger.exception(
                    "catalyst classification failed after insight upsert",
                    theme_id=theme.id,
                )
        await self.session.commit()
        elapsed_ms = int((time.monotonic() - started) * 1000)
        message = (
            f"题材事件已使用关键词降级更新（模型失败：{model_debug['model_error']}）"
            if degraded and model_debug.get("model_error")
            else (
                "题材事件已使用关键词降级更新"
                if degraded
                else "题材资料已更新"
            )
        )
        return ThemeInsightRefreshResponse(
            theme_id=theme.id,
            theme_name=theme.name,
            profile_updated=profile_updated,
            candidate_events=len(event_sources) + len(news_sources),
            inserted_events=inserted,
            updated_events=updated,
            ignored_events=max(
                0, len(event_sources) + len(news_sources) - len(event_rows)
            ),
            successful_sources=[source.publisher or source.url for source in sources],
            failed_sources=sorted(
                failed
                for failed in getattr(self.research, "failed_sources", set())
                if isinstance(failed, str)
            ),
            degraded=degraded,
            elapsed_ms=elapsed_ms,
            refreshed_at=now,
            message=message,
            model_name=model_debug.get("model_name"),
            model_error=model_debug.get("model_error"),
            model_reasoning=model_debug.get("model_reasoning"),
            model_raw_response=model_debug.get("model_raw_response"),
            source_count=len(sources),
        )
