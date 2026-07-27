"""个股 AI 买入/持有研判报告生成服务。"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_ai_report import StockAiReport
from app.repositories.news import NewsRepository
from app.repositories.stock_ai_report import StockAiReportRepository
from app.schemas.stock_ai_report import (
    DISCLAIMER,
    ExtractedStockAiReport,
    HorizonFit,
    HorizonSlot,
    StockAiReportHorizon,
    StockAiReportResponse,
    StockAiReportSections,
)
from app.services.concept_graph_refresh import model_error_message, parse_model_json
from app.services.model_provider import ModelProviderService
from app.services.short_term import ShortTermService
from app.services.stock import StockService
from app.services.theme import ThemeService

SYSTEM_PROMPT = """你是严谨的中国 A 股研究员。只能依据用户提供的市场上下文判断，不得编造未给出的财报数字、龙虎榜或未出现的新闻。
输出严格 JSON（不要 Markdown 解释），字段：
verdict: buy|watch|avoid
horizon: { short, swing, medium_long }，每项含 fit(suitable|neutral|unsuitable) 与 note
confidence: 0-100 整数
summary: 一句话核心结论
sections: { trend, emotion_rotation, themes_catalysts, stock_position, scenarios_actions, risks }
full_report: 连贯完整中文报告正文，须包含「供参考，非投资建议」
判断是否值得关注/买入，并说明短线、波段、中长线适配度。证据不足时倾向 watch，并在 risks 说明。"""

MAX_CONTEXT_CHARS = 9_000
MIN_REPORT_TIMEOUT_SECONDS = 120
MIN_REPORT_TOKENS = 4_096

FIT_LABEL: dict[HorizonFit, str] = {
    "suitable": "适合",
    "neutral": "中性",
    "unsuitable": "不适合",
}


def _format_horizon_text(slot: HorizonSlot) -> str:
    return f"{FIT_LABEL[slot.fit]} — {slot.note.strip()}"


def _parse_horizon_text(text: str) -> HorizonSlot:
    """从落库文案还原 horizon slot。"""
    for fit, label in FIT_LABEL.items():
        prefix = f"{label} — "
        if text.startswith(prefix):
            return HorizonSlot(fit=fit, note=text[len(prefix) :] or label)
    return HorizonSlot(fit="neutral", note=text or "暂无")


class StockAiReportService:
    def __init__(
        self,
        session: AsyncSession,
        user_id: int,
        *,
        providers: ModelProviderService | None = None,
        reports: StockAiReportRepository | None = None,
        stocks: StockService | None = None,
        short_term: ShortTermService | None = None,
        themes: ThemeService | None = None,
        news: NewsRepository | None = None,
    ):
        self.session = session
        self.user_id = user_id
        self.providers = providers or ModelProviderService(session, user_id)
        self.reports = reports or StockAiReportRepository(session)
        self.stocks = stocks or StockService(session)
        self.short_term = short_term or ShortTermService(session)
        self.themes = themes or ThemeService(session)
        self.news = news or NewsRepository(session)

    async def get_cached(self, code: str) -> StockAiReportResponse:
        row = await self.reports.get(self.user_id, code)
        if row is None:
            raise HTTPException(status_code=404, detail="尚未生成该股 AI 研判报告")
        return self._to_response(row)

    async def generate(self, code: str, *, force: bool = False) -> StockAiReportResponse:
        if not force:
            existing = await self.reports.get(self.user_id, code)
            if existing is not None:
                return self._to_response(existing)

        stock = await self.stocks.get_stock_detail(code)
        provider = await self.providers.get_default()

        started = time.monotonic()
        context, digest = await self._build_context(stock)
        user_prompt = (
            f"标的：{stock.name}({stock.code})\n"
            f"请基于下列上下文输出 JSON 研判。\n\n{context}"
        )

        adapter = self.providers.adapter(provider)
        # bump capacity for long reports
        if adapter.max_tokens < MIN_REPORT_TOKENS:
            adapter.max_tokens = MIN_REPORT_TOKENS
        timeout = max(int(provider.timeout_seconds or 60), MIN_REPORT_TIMEOUT_SECONDS)

        try:
            raw = await adapter.complete(
                SYSTEM_PROMPT,
                user_prompt,
                json_mode=True,
                reasoning=False,
                timeout_seconds=timeout,
            )
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise HTTPException(
                status_code=502,
                detail=f"模型调用失败：{model_error_message(exc)}",
            ) from exc

        try:
            extracted = ExtractedStockAiReport.model_validate(parse_model_json(raw))
        except (ValueError, ValidationError) as exc:
            raise HTTPException(
                status_code=502,
                detail=f"模型返回无法解析为研判报告：{str(exc)[:200]}",
            ) from exc

        elapsed_ms = int((time.monotonic() - started) * 1000)
        generated_at = datetime.now(UTC)
        row = await self.reports.upsert(
            user_id=self.user_id,
            stock_code=stock.code,
            stock_name=stock.name,
            verdict=extracted.verdict,
            horizon_short=_format_horizon_text(extracted.horizon.short),
            horizon_swing=_format_horizon_text(extracted.horizon.swing),
            horizon_medium_long=_format_horizon_text(extracted.horizon.medium_long),
            confidence=extracted.confidence,
            summary=extracted.summary,
            sections=extracted.sections.model_dump(),
            full_report=extracted.full_report,
            context_digest=digest,
            model_provider_id=provider.id,
            model_name=provider.model,
            elapsed_ms=elapsed_ms,
            generated_at=generated_at,
        )
        await self.session.commit()
        return self._to_response(row)

    async def _build_context(self, stock: Any) -> tuple[str, dict[str, Any]]:
        missing: list[str] = ["first_to_second"]
        digest: dict[str, Any] = {
            "stock_code": stock.code,
            "stock_name": stock.name,
            "missing_sources": missing,
        }
        parts: list[str] = []

        events = [
            f"- {e.title}" + (f"（{e.published_at}）" if e.published_at else "")
            for e in (stock.recent_events or [])[:5]
        ]
        parts.append(
            "【个股】\n"
            f"代码 {stock.code} 名称 {stock.name} 行业 {stock.industry or '未知'}\n"
            f"现价 {stock.current_price} 涨跌幅 {stock.rise_fall_pct}% 市值 {stock.market_cap}\n"
            "近期事件：\n" + ("\n".join(events) if events else "- 暂无")
        )

        try:
            overview = await self.short_term.analyze_from_database(period="today")
            card = overview.strategy_card
            digest["market_emotion"] = overview.market_emotion
            digest["core_conclusion"] = overview.core_conclusion
            parts.append(
                "【短线概览】\n"
                f"情绪：{overview.market_emotion}\n"
                f"展望：{overview.short_term_outlook}\n"
                f"建议：{overview.operation_advice}\n"
                f"结论：{overview.core_conclusion}\n"
                f"跟踪：{', '.join(overview.tracking_focus or [])}\n"
                + (
                    f"策略卡：主{card.primary_strategy}/辅{card.secondary_strategy}；"
                    f"指数{card.index_strength} 情绪{card.emotion_strength}\n"
                    if card
                    else ""
                )
            )
        except Exception as exc:  # noqa: BLE001 — 子源失败不阻断
            missing.append("short_term")
            parts.append(f"【短线概览】不可用：{str(exc)[:120]}")

        try:
            hot = await self.themes.get_ranking(limit=8)
            rising = await self.themes.list_themes(
                page=1, page_size=8, sort_by="rise_fall_pct", sort_order="desc"
            )
            digest["hot_themes"] = [i.name for i in hot.items[:5]]
            digest["rising_themes"] = [i.name for i in rising.items[:5]]
            hot_lines = [
                f"- {i.name} 热度{i.heat_index} 涨跌{i.rise_fall_pct}%" for i in hot.items
            ]
            rise_lines = [
                f"- {i.name} 涨跌{i.rise_fall_pct}% 热度{i.heat_index}"
                for i in rising.items
            ]
            parts.append(
                "【热门题材】\n"
                + ("\n".join(hot_lines) or "- 暂无")
                + "\n【涨幅题材】\n"
                + ("\n".join(rise_lines) or "- 暂无")
            )
        except Exception as exc:  # noqa: BLE001
            missing.append("themes")
            parts.append(f"【题材】不可用：{str(exc)[:120]}")

        try:
            articles, _ = await self.news.list_latest(limit=12)
            digest["news_count"] = len(articles)
            news_lines = [
                f"- {a.title}" + (f" | {a.source}" if a.source else "")
                for a in articles[:12]
            ]
            parts.append("【新闻】\n" + ("\n".join(news_lines) or "- 暂无"))
        except Exception as exc:  # noqa: BLE001
            missing.append("news")
            parts.append(f"【新闻】不可用：{str(exc)[:120]}")

        parts.append(
            "【说明】一进二/涨停链实时池未纳入本次上下文（避免拖慢研判）；"
            "请勿臆造龙虎榜细节。输出须含免责声明。"
        )
        digest["missing_sources"] = missing

        text = "\n\n".join(parts)
        if len(text) > MAX_CONTEXT_CHARS:
            text = text[: MAX_CONTEXT_CHARS - 20] + "\n…(已截断)"
        return text, digest

    def _to_response(self, row: StockAiReport) -> StockAiReportResponse:
        sections_data = row.sections if isinstance(row.sections, dict) else {}
        sections = StockAiReportSections.model_validate(sections_data)
        horizon = StockAiReportHorizon(
            short=_parse_horizon_text(row.horizon_short),
            swing=_parse_horizon_text(row.horizon_swing),
            medium_long=_parse_horizon_text(row.horizon_medium_long),
        )
        return StockAiReportResponse(
            code=row.stock_code,
            stock_name=row.stock_name,
            verdict=row.verdict,  # type: ignore[arg-type]
            horizon=horizon,
            confidence=row.confidence,
            summary=row.summary,
            sections=sections,
            full_report=row.full_report,
            model_name=row.model_name,
            generated_at=row.generated_at,
            elapsed_ms=row.elapsed_ms,
            disclaimer=DISCLAIMER,
        )