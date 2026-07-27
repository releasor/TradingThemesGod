"""一进二候选实时筛选服务。"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import akshare as ak
import httpx
import pandas as pd
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.theme_insights import normalize_stock_code
from app.schemas.short_term import (
    FirstToSecondCandidateItem,
    FirstToSecondCandidateResponse,
)
from app.services.model_provider import ModelProviderService, model_http_error_message


def _previous_weekday(value: date) -> date:
    from app.services.trading_calendar import TradingCalendar

    return TradingCalendar.previous_trade_day(value)


def _first_present(row: pd.Series, names: tuple[str, ...]) -> Any:
    for name in names:
        if name in row and pd.notna(row[name]):
            return row[name]
    return None


def _number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.replace(",", "").replace("%", "").strip()
        if not value or value in {"-", "--"}:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _money_to_yi(value: Any) -> float | None:
    number = _number(value)
    if number is None:
        return None
    if abs(number) > 10000:
        return round(number / 100000000, 2)
    return round(number, 2)


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "是", "一字", "一字板", "炸板"}


@dataclass(frozen=True)
class RawFirstToSecondStock:
    code: str
    name: str
    theme_name: str | None
    price: float | None
    market_cap: float | None
    float_market_cap: float | None
    turnover_rate: float | None
    amount: float | None
    first_limit_up_at: str | None
    open_board_count: int
    streak_days: int
    is_one_word: bool
    is_failed: bool
    is_today_limit_up: bool
    is_today_near_limit_up: bool


class FirstToSecondProvider:
    """一进二源数据提供器，默认使用 AKShare。"""

    async def fetch_previous_first_limit_up(self, trade_date: date) -> pd.DataFrame:
        return await asyncio.to_thread(
            ak.stock_zt_pool_previous_em, date=trade_date.strftime("%Y%m%d")
        )

    async def fetch_today_limit_up(self, trade_date: date) -> pd.DataFrame:
        return await asyncio.to_thread(
            ak.stock_zt_pool_em, date=trade_date.strftime("%Y%m%d")
        )

    async def fetch_today_near_limit_up(self, trade_date: date) -> pd.DataFrame:
        fetcher = getattr(ak, "stock_zt_pool_zbgc_em", None)
        if fetcher is None:
            return pd.DataFrame()
        return await asyncio.to_thread(fetcher, date=trade_date.strftime("%Y%m%d"))


class FirstToSecondService:
    """筛选昨日首板到今日一进二候选。"""

    def __init__(
        self,
        session: AsyncSession,
        provider: FirstToSecondProvider | None = None,
        model_service: ModelProviderService | None = None,
    ):
        self.session = session
        self.provider = provider or FirstToSecondProvider()
        self.model_service = model_service

    async def get_candidates(
        self, trade_date: date | None = None, *, force_refresh: bool = False
    ) -> FirstToSecondCandidateResponse:
        from app.services.trading_calendar import TradingCalendar

        target_date = TradingCalendar.resolve(trade_date)
        previous_date = TradingCalendar.previous_trade_day(target_date)
        source_status: dict[str, str] = {}
        missing_sources: list[str] = []

        try:
            previous_frame, today_limit_frame, today_near_frame = await asyncio.gather(
                self.provider.fetch_previous_first_limit_up(previous_date),
                self.provider.fetch_today_limit_up(target_date),
                self.provider.fetch_today_near_limit_up(target_date),
            )
            source_status["limit_pool"] = "success"
        except Exception as exc:
            source_status["limit_pool"] = f"failed:{str(exc)[:120]}"
            missing_sources.append("limit_pool")
            previous_frame = today_limit_frame = today_near_frame = pd.DataFrame()

        rows = self._normalize_rows(previous_frame, today_limit_frame, today_near_frame)
        candidates, excluded_count = self._score_rows(rows)
        await self._enrich_with_model(candidates, source_status, missing_sources)

        return FirstToSecondCandidateResponse(
            trade_date=target_date,
            previous_trade_date=previous_date,
            refreshed_at=datetime.now(UTC).isoformat(),
            degraded=bool(missing_sources),
            missing_sources=missing_sources,
            candidates=candidates,
            excluded_count=excluded_count,
            source_status=source_status,
        )

    def _normalize_rows(
        self,
        previous_frame: pd.DataFrame,
        today_limit_frame: pd.DataFrame,
        today_near_frame: pd.DataFrame,
    ) -> list[RawFirstToSecondStock]:
        today_limit_codes = self._codes(today_limit_frame)
        today_near_codes = self._codes(today_near_frame)
        rows: list[RawFirstToSecondStock] = []
        for _, row in previous_frame.iterrows():
            raw_code = _first_present(row, ("代码", "股票代码", "code"))
            if raw_code is None:
                continue
            code = normalize_stock_code(raw_code)
            open_board_count = int(
                _number(_first_present(row, ("开板次数", "炸板次数", "open_board_count")))
                or 0
            )
            streak_days = int(
                _number(_first_present(row, ("连续涨停", "连板数", "streak_days"))) or 1
            )
            is_failed = _boolish(_first_present(row, ("是否炸板", "炸板", "is_failed")))
            is_one_word = _boolish(
                _first_present(row, ("是否一字板", "一字板", "is_one_word"))
            )
            first_limit_up_at = _first_present(
                row, ("首次封板时间", "首次涨停时间", "first_limit_up_at")
            )
            rows.append(
                RawFirstToSecondStock(
                    code=code,
                    name=str(_first_present(row, ("名称", "股票简称", "name")) or code),
                    theme_name=self._theme_name(row),
                    price=_number(_first_present(row, ("最新价", "收盘价", "price"))),
                    market_cap=_money_to_yi(_first_present(row, ("总市值", "market_cap"))),
                    float_market_cap=_money_to_yi(
                        _first_present(row, ("流通市值", "流通盘", "float_market_cap"))
                    ),
                    turnover_rate=_number(_first_present(row, ("换手率", "turnover_rate"))),
                    amount=_money_to_yi(_first_present(row, ("成交额", "amount"))),
                    first_limit_up_at=str(first_limit_up_at) if first_limit_up_at else None,
                    open_board_count=open_board_count,
                    streak_days=streak_days,
                    is_one_word=is_one_word,
                    is_failed=is_failed or open_board_count > 0,
                    is_today_limit_up=code in today_limit_codes,
                    is_today_near_limit_up=code in today_near_codes,
                )
            )
        return rows

    @staticmethod
    def _codes(frame: pd.DataFrame) -> set[str]:
        if frame.empty:
            return set()
        column = next((name for name in ("代码", "股票代码", "code") if name in frame), None)
        if column is None:
            return set()
        return {normalize_stock_code(value) for value in frame[column].dropna().tolist()}

    @staticmethod
    def _theme_name(row: pd.Series) -> str | None:
        value = _first_present(row, ("所属行业", "所属概念", "题材", "theme_name"))
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _score_rows(
        self, rows: list[RawFirstToSecondStock]
    ) -> tuple[list[FirstToSecondCandidateItem], int]:
        items: list[FirstToSecondCandidateItem] = []
        excluded_count = 0
        for row in rows:
            item = self._score_row(row)
            if item.decision == "excluded":
                excluded_count += 1
                continue
            items.append(item)

        items.sort(
            key=lambda item: (
                item.theme_name or "",
                item.first_limit_up_at or "99:99:99",
                -item.score,
            )
        )
        items.sort(key=lambda item: item.score, reverse=True)
        return items[:20], excluded_count

    def _score_row(self, row: RawFirstToSecondStock) -> FirstToSecondCandidateItem:
        score = 50
        matched: list[str] = []
        excluded: list[str] = []
        risk_flags: list[str] = []
        catalysts: list[str] = []

        if row.price is not None and row.price > 25:
            excluded.append("股价 25 元以上")
        if row.float_market_cap is not None and row.float_market_cap < 10:
            excluded.append("流通市值小于 10 亿")
        if row.float_market_cap is not None and row.float_market_cap > 100:
            excluded.append("流通市值大于 100 亿")
        if row.is_failed:
            excluded.append("昨日首板炸板")
        if row.is_one_word:
            excluded.append("昨日首板一字板")
        if (row.amount or 0) < 1 and (row.turnover_rate or 0) < 2:
            excluded.append("流动性不足")

        if row.is_today_limit_up:
            score += 25
            matched.append("今日仍在涨停池")
        elif row.is_today_near_limit_up:
            score += 12
            matched.append("今日接近异动")
            risk_flags.append("未确认涨停")
        else:
            score -= 15
            risk_flags.append("今日未进入涨停池")

        if row.float_market_cap is not None and 20 <= row.float_market_cap <= 80:
            score += 10
            matched.append("流通市值 20-80 亿")
        if row.market_cap is not None and 50 <= row.market_cap <= 150:
            score += 8
            matched.append("总市值 50-150 亿")
        if row.first_limit_up_at:
            score += 5
            matched.append(f"昨日首封时间 {row.first_limit_up_at}")
        if row.theme_name:
            score += 5
            matched.append(f"题材/行业：{row.theme_name}")
            catalysts.append(f"行业催化：{row.theme_name}")

        decision = "excluded" if excluded else "candidate" if score >= 70 else "watch"
        if excluded:
            score = min(score, 49)
        score = max(0, min(100, score))

        return FirstToSecondCandidateItem(
            code=row.code,
            name=row.name,
            theme_name=row.theme_name,
            price=row.price,
            market_cap=row.market_cap,
            float_market_cap=row.float_market_cap,
            turnover_rate=row.turnover_rate,
            amount=row.amount,
            first_limit_up_at=row.first_limit_up_at,
            open_board_count=row.open_board_count,
            score=int(score),
            decision=decision,
            matched_rules=matched,
            excluded_rules=excluded,
            risk_flags=risk_flags,
            catalysts=catalysts,
            operation_advice=self._operation_advice(decision),
            core_conclusion=self._core_conclusion(decision),
        )

    @staticmethod
    def _operation_advice(decision: str) -> str:
        if decision == "candidate":
            return "只做换手晋级确认，盘中放量回封优先，缩量一致谨慎。"
        if decision == "watch":
            return "观察竞价和承接强度，未转强不打板。"
        return "硬性条件不符合，放弃一进二打板。"

    @staticmethod
    def _core_conclusion(decision: str) -> str:
        if decision == "candidate":
            return "具备一进二观察价值。"
        if decision == "watch":
            return "仅保留观察，等待盘中确认。"
        return "不符合一进二候选。"

    async def _enrich_with_model(
        self,
        candidates: list[FirstToSecondCandidateItem],
        source_status: dict[str, str],
        missing_sources: list[str],
    ) -> None:
        if not candidates:
            source_status["model_catalyst"] = "skipped:no_candidates"
            return
        if self.model_service is None:
            source_status["model_catalyst"] = "missing"
            missing_sources.append("model_catalyst")
            return
        try:
            provider = await self.model_service.get_default()
            adapter = self.model_service.adapter(provider)
            payload = [
                {
                    "code": item.code,
                    "name": item.name,
                    "theme": item.theme_name,
                    "matched_rules": item.matched_rules,
                }
                for item in candidates[:10]
            ]
            text = await adapter.complete(
                "你是A股短线复盘助手，只返回JSON数组。",
                "基于输入候选，补充每只股票的一进二催化，字段为 code, catalysts。"
                f"不要编造不存在的信息，没有明确催化返回空数组。输入：{json.dumps(payload, ensure_ascii=False)}",
                json_mode=True,
                reasoning=False,
                timeout_seconds=30,
            )
            self._merge_model_catalysts(candidates, text)
            source_status["model_catalyst"] = "success"
        except HTTPException:
            source_status["model_catalyst"] = "missing"
            missing_sources.append("model_catalyst")
        except Exception as exc:  # noqa: BLE001 — 模型失败不得拖垮候选接口
            detail = (
                model_http_error_message(exc)
                if isinstance(exc, httpx.HTTPError)
                else str(exc)[:120]
            )
            source_status["model_catalyst"] = f"failed:{detail}"
            missing_sources.append("model_catalyst")

    @staticmethod
    def _merge_model_catalysts(
        candidates: list[FirstToSecondCandidateItem], text: str
    ) -> None:
        payload = json.loads(text)
        if not isinstance(payload, list):
            return
        by_code = {item.code: item for item in candidates}
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            item = by_code.get(str(entry.get("code", "")))
            catalysts = entry.get("catalysts")
            if item is None or not isinstance(catalysts, list):
                continue
            item.catalysts.extend(str(value) for value in catalysts if value)
