"""StockAiReportService 单元测试。"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.schemas.stock_ai_report import StockAiReportResponse
from app.services.stock_ai_report import StockAiReportService

VALID_MODEL_JSON = """{
  "verdict": "watch",
  "horizon": {
    "short": {"fit": "suitable", "note": "情绪偏强可短线观察"},
    "swing": {"fit": "neutral", "note": "波段需等回撤"},
    "medium_long": {"fit": "unsuitable", "note": "缺乏长期逻辑"}
  },
  "confidence": 62,
  "summary": "短期可观察，不宜追高。",
  "sections": {
    "trend": "趋势中性",
    "emotion_rotation": "情绪偏强",
    "themes_catalysts": "主线暂不明",
    "stock_position": "涨幅一般",
    "scenarios_actions": "等确认再动手",
    "risks": "追高风险"
  },
  "full_report": "完整报告正文。供参考，非投资建议。"
}"""


def _stock():
    return SimpleNamespace(
        id=1,
        code="600519",
        name="贵州茅台",
        industry="白酒",
        market_cap=1,
        current_price=1600,
        rise_fall_pct=1.2,
        recent_events=[],
    )


def _make_service(**overrides):
    session = AsyncMock()
    providers = MagicMock()
    reports = MagicMock()
    stocks = MagicMock()
    short_term = MagicMock()
    themes = MagicMock()
    news = MagicMock()

    stocks.get_stock_detail = AsyncMock(return_value=_stock())
    short_term.analyze_from_database = AsyncMock(
        return_value=SimpleNamespace(
            market_emotion="情绪强",
            short_term_outlook="观察",
            operation_advice="谨慎",
            core_conclusion="中性",
            tracking_focus=["白酒"],
            strategy_card=None,
        )
    )
    themes.get_ranking = AsyncMock(
        return_value=SimpleNamespace(items=[SimpleNamespace(name="白酒", heat_index=80, rise_fall_pct=1)])
    )
    themes.list_themes = AsyncMock(
        return_value=SimpleNamespace(
            items=[SimpleNamespace(name="白酒", heat_index=80, rise_fall_pct=2)]
        )
    )
    news.list_latest = AsyncMock(return_value=([], 0))
    reports.get = AsyncMock(return_value=None)
    reports.upsert = AsyncMock(
        side_effect=lambda **kwargs: SimpleNamespace(
            stock_code=kwargs["stock_code"],
            stock_name=kwargs["stock_name"],
            verdict=kwargs["verdict"],
            horizon_short=kwargs["horizon_short"],
            horizon_swing=kwargs["horizon_swing"],
            horizon_medium_long=kwargs["horizon_medium_long"],
            confidence=kwargs["confidence"],
            summary=kwargs["summary"],
            sections=kwargs["sections"],
            full_report=kwargs["full_report"],
            model_name=kwargs["model_name"],
            generated_at=kwargs["generated_at"],
            elapsed_ms=kwargs["elapsed_ms"],
        )
    )

    service = StockAiReportService(
        session,
        user_id=7,
        providers=providers,
        reports=reports,
        stocks=stocks,
        short_term=short_term,
        themes=themes,
        news=news,
    )
    for key, value in overrides.items():
        setattr(service, key, value)
    return service, session, providers, reports


@pytest.mark.asyncio
async def test_generate_without_default_model_raises_409():
    service, _, providers, reports = _make_service()
    providers.get_default = AsyncMock(
        side_effect=HTTPException(409, "请先在模型设置中配置并启用默认模型")
    )

    with pytest.raises(HTTPException) as exc:
        await service.generate("600519", force=True)

    assert exc.value.status_code == 409
    reports.upsert.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_force_false_returns_cache():
    cached = SimpleNamespace(
        stock_code="600519",
        stock_name="贵州茅台",
        verdict="buy",
        horizon_short="适合 — 短线强",
        horizon_swing="中性 — 波段一般",
        horizon_medium_long="不适合 — 估值高",
        confidence=70,
        summary="可短线关注",
        sections={
            "trend": "t",
            "emotion_rotation": "e",
            "themes_catalysts": "c",
            "stock_position": "s",
            "scenarios_actions": "a",
            "risks": "r",
        },
        full_report="正文",
        model_name="gpt",
        generated_at=datetime(2026, 7, 24, tzinfo=UTC),
        elapsed_ms=100,
    )
    service, _, providers, reports = _make_service()
    reports.get = AsyncMock(return_value=cached)

    result = await service.generate("600519", force=False)

    assert isinstance(result, StockAiReportResponse)
    assert result.verdict == "buy"
    assert result.summary == "可短线关注"
    providers.get_default.assert_not_called()


@pytest.mark.asyncio
async def test_generate_persists_valid_model_json():
    service, session, providers, reports = _make_service()
    provider = SimpleNamespace(id=3, model="demo-model", timeout_seconds=60)
    providers.get_default = AsyncMock(return_value=provider)
    adapter = MagicMock()
    adapter.max_tokens = 2048
    adapter.complete = AsyncMock(return_value=VALID_MODEL_JSON)
    providers.adapter.return_value = adapter

    result = await service.generate("600519", force=True)

    assert result.verdict == "watch"
    assert result.confidence == 62
    assert "非投资建议" in result.full_report or "供参考" in result.disclaimer
    reports.upsert.assert_awaited_once()
    session.commit.assert_awaited_once()
    assert adapter.max_tokens >= 4096


@pytest.mark.asyncio
async def test_invalid_model_json_raises_502_without_upsert():
    service, _, providers, reports = _make_service()
    providers.get_default = AsyncMock(
        return_value=SimpleNamespace(id=1, model="m", timeout_seconds=60)
    )
    adapter = MagicMock()
    adapter.max_tokens = 8192
    adapter.complete = AsyncMock(return_value="not-json")
    providers.adapter.return_value = adapter

    with pytest.raises(HTTPException) as exc:
        await service.generate("600519", force=True)

    assert exc.value.status_code == 502
    reports.upsert.assert_not_awaited()
