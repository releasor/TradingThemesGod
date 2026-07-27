"""策略卡题材行情刷新：东方财富优先，超时后自动切换 AKShare。"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import akshare as ak

from app.core.config import get_settings
from app.core.logging import get_logger
from app.scrapers.anti_scraping import AntiScrapingMiddleware
from app.scrapers.eastmoney import EastMoneyScraper

logger = get_logger(__name__)

EASTMONEY_QUOTE_TIMEOUT_SECONDS = 18
OVERALL_QUOTE_TIMEOUT_SECONDS = 22
MIN_QUOTE_SUCCESS_COUNT = 1


@dataclass(frozen=True)
class StrategyQuoteRefreshResult:
    trade_date: date
    source: str
    elapsed_ms: int
    attempts: tuple[str, ...] = field(default_factory=tuple)
    updated_count: int = 0


def _normalize_board_code(code: str) -> str:
    value = str(code).strip().upper()
    return value if value.startswith("BK") else f"BK{value}"


def _parse_akshare_themes(frame: Any, codes: set[str]) -> list[dict[str, Any]]:
    normalized = {_normalize_board_code(code) for code in codes}
    themes: list[dict[str, Any]] = []
    code_column = "板块代码" if "板块代码" in frame.columns else None
    if code_column is None:
        return themes

    for _, row in frame.iterrows():
        code = _normalize_board_code(row[code_column])
        if code not in normalized:
            continue
        name = str(row.get("板块名称", "")).strip()
        if not name:
            continue
        rise_fall_pct = row.get("涨跌幅")
        heat_index = row.get("换手率")
        up_count = row.get("上涨家数")
        stock_count = None
        if up_count is not None:
            try:
                down_count = int(row.get("下跌家数") or 0)
                stock_count = int(up_count) + down_count
            except (TypeError, ValueError):
                stock_count = None
        themes.append(
            {
                "name": name,
                "code": code,
                "heat_index": _to_optional_decimal(heat_index),
                "rise_fall_pct": _to_optional_decimal(rise_fall_pct),
                "stock_count": stock_count,
                "category": None,
                "source": "akshare",
            }
        )
    return themes


def _to_optional_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except Exception:
        return None


async def _refresh_via_eastmoney(codes: set[str]) -> tuple[date | None, int]:
    settings = get_settings()
    middleware = AntiScrapingMiddleware(
        proxy_url=settings.PROXY_URL if settings.PROXY_ENABLED else None,
        min_interval=0.2,
        max_interval=0.6,
        max_retries=1,
    )
    scraper = EastMoneyScraper(middleware=middleware)
    try:
        return await asyncio.wait_for(
            scraper.refresh_theme_quotes(only_codes=codes),
            timeout=EASTMONEY_QUOTE_TIMEOUT_SECONDS,
        )
    finally:
        await scraper.close()


async def _refresh_via_akshare(codes: set[str]) -> tuple[date | None, list[dict[str, Any]]]:
    frame = await asyncio.wait_for(
        asyncio.to_thread(ak.stock_board_concept_name_em),
        timeout=AKSHARE_QUOTE_TIMEOUT_SECONDS,
    )
    themes = _parse_akshare_themes(frame, codes)
    if not themes:
        return None, []
    settings = get_settings()
    middleware = AntiScrapingMiddleware(
        proxy_url=settings.PROXY_URL if settings.PROXY_ENABLED else None,
    )
    scraper = EastMoneyScraper(middleware=middleware)
    try:
        await scraper._save_themes(themes)
    finally:
        await scraper.close()
    return date.today(), themes


async def refresh_strategy_quotes(codes: set[str]) -> StrategyQuoteRefreshResult:
    """按优先级刷新策略题材行情，并记录耗时与数据源。"""
    try:
        return await asyncio.wait_for(
            _refresh_strategy_quotes_inner(codes),
            timeout=OVERALL_QUOTE_TIMEOUT_SECONDS,
        )
    except TimeoutError as exc:
        elapsed_ms = int(OVERALL_QUOTE_TIMEOUT_SECONDS * 1000)
        raise RuntimeError(
            f"题材行情刷新超时（>{OVERALL_QUOTE_TIMEOUT_SECONDS} 秒），已回退数据库数据"
        ) from exc


async def _refresh_strategy_quotes_inner(
    codes: set[str],
) -> StrategyQuoteRefreshResult:
    started = time.monotonic()
    attempts: list[str] = []
    normalized_codes = {_normalize_board_code(code) for code in codes}

    try:
        attempts.append("东方财富")
        trade_date, updated_count = await _refresh_via_eastmoney(normalized_codes)
        if trade_date is not None and updated_count >= MIN_QUOTE_SUCCESS_COUNT:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "strategy_quote_refresh_success",
                source="eastmoney",
                elapsed_ms=elapsed_ms,
                updated_count=updated_count,
            )
            return StrategyQuoteRefreshResult(
                trade_date=trade_date,
                source="eastmoney",
                elapsed_ms=elapsed_ms,
                attempts=tuple(attempts),
                updated_count=updated_count,
            )
        if trade_date is not None and updated_count > 0:
            logger.warning(
                "strategy_quote_refresh_partial",
                source="eastmoney",
                updated_count=updated_count,
                required=MIN_QUOTE_SUCCESS_COUNT,
            )
    except TimeoutError:
        logger.warning(
            "strategy_quote_refresh_timeout",
            source="eastmoney",
            timeout_seconds=EASTMONEY_QUOTE_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.warning("strategy_quote_refresh_failed", source="eastmoney", error=str(exc))

    elapsed_ms = int((time.monotonic() - started) * 1000)
    attempts_text = "、".join(attempts) if attempts else "无"
    raise RuntimeError(
        f"题材行情刷新失败（已尝试 {attempts_text}，耗时 {elapsed_ms / 1000:.1f} 秒），已回退数据库数据"
    )
