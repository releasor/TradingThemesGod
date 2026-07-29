"""题材按 (source, code) 加载与行情回写。"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.models.theme import Theme

logger = get_logger(__name__)


async def load_themes_map_for_source(
    session: AsyncSession,
    *,
    source: str,
    codes: list[str],
) -> dict[str, Theme]:
    """返回 code -> Theme，仅限指定 source 且未软删。"""
    if not codes:
        return {}
    result = await session.execute(
        select(Theme).where(
            Theme.source == source,
            Theme.code.in_(codes),
            Theme.deleted_at.is_(None),
        )
    )
    return {t.code: t for t in result.scalars().all()}


def _as_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except Exception:
        return None


def _is_zero_quote(value: Any) -> bool:
    parsed = _as_decimal(value)
    return parsed is None or parsed == 0


def batch_quotes_are_all_zero(themes: list[dict[str, Any]]) -> bool:
    """整批涨跌幅均为 0/空（盘后接口常见），不可用来覆盖已有有效行情。"""
    if not themes:
        return True
    return all(_is_zero_quote(item.get("rise_fall_pct")) for item in themes)


async def apply_theme_quotes(
    themes: list[dict[str, Any]],
    *,
    preserve_nonzero_when_batch_zero: bool = True,
) -> int:
    """按板块 code 回写涨跌幅/热度到所有源的同名行（东财与 AKShare 共用 BK）。

    盘后接口常返回全 0：若 ``preserve_nonzero_when_batch_zero`` 为真，则不覆盖
    库内已有的非零涨跌幅，避免「已写入」却把看板刷空。
    """
    if not themes:
        return 0

    quote_by_code = {
        str(item.get("code", "")).strip().upper(): item
        for item in themes
        if item.get("code")
    }
    codes = list(quote_by_code)
    if not codes:
        return 0

    skip_zero_overwrite = preserve_nonzero_when_batch_zero and batch_quotes_are_all_zero(
        themes
    )
    updated = 0

    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(Theme).where(
                    Theme.code.in_(codes),
                    Theme.deleted_at.is_(None),
                )
            )
        ).scalars().all()

        for theme in rows:
            data = quote_by_code.get(theme.code)
            if data is None:
                continue

            name = data.get("name")
            if name:
                theme.name = str(name).strip() or theme.name

            heat = _as_decimal(data.get("heat_index"))
            if heat is not None:
                theme.heat_index = heat

            stock_count = data.get("stock_count")
            if stock_count is not None:
                try:
                    theme.stock_count = int(stock_count)
                except (TypeError, ValueError):
                    pass

            new_rise = _as_decimal(data.get("rise_fall_pct"))
            if new_rise is not None:
                old = theme.rise_fall_pct
                if (
                    skip_zero_overwrite
                    and new_rise == 0
                    and old is not None
                    and old != 0
                ):
                    pass
                else:
                    theme.rise_fall_pct = new_rise

            updated += 1

        await session.commit()

    if skip_zero_overwrite:
        logger.info(
            "theme_quotes_preserved_nonzero",
            matched_rows=updated,
            incoming_codes=len(codes),
        )
    else:
        logger.info(
            "theme_quotes_applied",
            matched_rows=updated,
            incoming_codes=len(codes),
        )
    return updated
