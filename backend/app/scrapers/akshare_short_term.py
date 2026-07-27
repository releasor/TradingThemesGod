"""AkShare 短线信号与龙虎榜默认拉取。"""

from __future__ import annotations

import asyncio
import math
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

import akshare as ak
import pandas as pd

from app.core.logging import get_logger

logger = get_logger(__name__)


def _date_str(trade_date: date) -> str:
    return trade_date.strftime("%Y%m%d")


def _json_safe(value: Any) -> Any:
    """把 AkShare / pandas 值转成 JSON 可序列化结构。"""
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (datetime, date, time, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "item") and callable(value.item):
        try:
            return _json_safe(value.item())
        except (ValueError, TypeError):
            return None
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _frame_to_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame is None or frame.empty:
        return []
    # 统一把 NaN 转成 None，并去掉 date/Timestamp 等不可 JSON 序列化类型
    cleaned = frame.where(pd.notna(frame), None)
    return [_json_safe(row) for row in cleaned.to_dict(orient="records")]

async def _safe_fetch(label: str, callable_, **kwargs) -> pd.DataFrame:
    try:
        frame = await asyncio.to_thread(callable_, **kwargs)
        if frame is None:
            return pd.DataFrame()
        return frame
    except Exception as exc:  # noqa: BLE001
        logger.warning("akshare_short_term_fetch_failed", source=label, error=str(exc))
        return pd.DataFrame()


async def fetch_limit_pools(trade_date: date) -> dict[str, list[dict[str, Any]]]:
    """拉取当日涨停 / 炸板 / 接近涨停池，供 ShortTermSignalScraper 使用。"""
    day = _date_str(trade_date)
    limit_up, failed, near = await asyncio.gather(
        _safe_fetch("limit_up", ak.stock_zt_pool_em, date=day),
        _safe_fetch("failed_limit_up", ak.stock_zt_pool_zbgc_em, date=day),
        _safe_fetch("near_limit_up", ak.stock_zt_pool_strong_em, date=day),
    )

    # 一字板：从涨停池里筛「是否一字」类字段，或封板时间极早且开板次数为 0
    one_word_rows: list[dict[str, Any]] = []
    for row in _frame_to_rows(limit_up):
        flag = row.get("是否一字板") or row.get("一字板") or row.get("涨停形态")
        text = str(flag or "")
        if "一字" in text:
            one_word_rows.append(row)

    pools = {
        "limit_up": _frame_to_rows(limit_up),
        "failed_limit_up": _frame_to_rows(failed),
        "near_limit_up": _frame_to_rows(near),
        "one_word_limit_up": one_word_rows,
    }
    if not any(pools.values()):
        raise RuntimeError(f"AkShare 涨停相关池均为空（{day}），可能非交易日或源不可用")
    return pools


async def fetch_dragon_tiger_entries(trade_date: date) -> list[dict[str, Any]]:
    """拉取当日龙虎榜明细。"""
    day = _date_str(trade_date)
    frame = await _safe_fetch(
        "dragon_tiger",
        ak.stock_lhb_detail_em,
        start_date=day,
        end_date=day,
    )
    rows = _frame_to_rows(frame)
    if not rows:
        raise RuntimeError(f"AkShare 龙虎榜为空（{day}），可能非交易日或源不可用")
    return rows
