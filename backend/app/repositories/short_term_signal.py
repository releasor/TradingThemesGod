"""短线雷达五表仓储。"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.short_term_signal import (
    DailyStockSignal,
    DragonTigerEntry,
    SectorRotationSnapshot,
    ShortTermCandidate,
    ShortTermSignalRun,
)


class ShortTermSignalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_run(self, trade_date: date) -> ShortTermSignalRun:
        run = ShortTermSignalRun(
            trade_date=trade_date,
            status="running",
            started_at=datetime.now(timezone.utc),
            source_status={},
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def finish_run(
        self,
        run: ShortTermSignalRun,
        *,
        status: str,
        source_status: dict[str, Any],
        error_message: str | None = None,
    ) -> ShortTermSignalRun:
        run.status = status
        run.source_status = source_status
        run.error_message = error_message
        run.finished_at = datetime.now(timezone.utc)
        await self.session.flush()
        return run

    async def upsert_signal(self, payload: dict[str, Any]) -> DailyStockSignal:
        existing = await self.session.scalar(
            select(DailyStockSignal).where(
                DailyStockSignal.trade_date == payload["trade_date"],
                DailyStockSignal.stock_id == payload["stock_id"],
                DailyStockSignal.signal_type == payload["signal_type"],
            )
        )
        row = existing or DailyStockSignal(
            trade_date=payload["trade_date"],
            stock_id=payload["stock_id"],
            signal_type=payload["signal_type"],
        )
        if existing is None:
            self.session.add(row)

        for key in (
            "theme_id",
            "limit_up_order",
            "first_limit_up_at",
            "last_limit_up_at",
            "open_board_count",
            "streak_days",
            "is_one_word",
            "is_failed",
            "price",
            "turnover_rate",
            "amount",
            "market_cap",
            "float_market_cap",
            "source",
            "source_payload",
        ):
            if key in payload:
                setattr(row, key, payload[key])

        await self.session.flush()
        return row

    async def upsert_signals(self, rows: list[dict[str, Any]]) -> int:
        for payload in rows:
            await self.upsert_signal(payload)
        return len(rows)

    async def upsert_dragon_tiger(self, payload: dict[str, Any]) -> DragonTigerEntry:
        existing = await self.session.scalar(
            select(DragonTigerEntry).where(
                DragonTigerEntry.trade_date == payload["trade_date"],
                DragonTigerEntry.stock_id == payload["stock_id"],
                DragonTigerEntry.reason == payload.get("reason", ""),
            )
        )
        row = existing or DragonTigerEntry(
            trade_date=payload["trade_date"],
            stock_id=payload["stock_id"],
            reason=payload.get("reason", ""),
        )
        if existing is None:
            self.session.add(row)
        for key in (
            "buy_amount",
            "sell_amount",
            "net_amount",
            "seat_summary",
            "source",
            "source_payload",
        ):
            if key in payload:
                setattr(row, key, payload[key])
        await self.session.flush()
        return row

    async def upsert_dragon_tiger_entries(self, rows: list[dict[str, Any]]) -> int:
        for payload in rows:
            await self.upsert_dragon_tiger(payload)
        return len(rows)

    async def upsert_sector_snapshot(self, payload: dict[str, Any]) -> SectorRotationSnapshot:
        existing = await self.session.scalar(
            select(SectorRotationSnapshot).where(
                SectorRotationSnapshot.trade_date == payload["trade_date"],
                SectorRotationSnapshot.theme_id == payload["theme_id"],
            )
        )
        row = existing or SectorRotationSnapshot(
            trade_date=payload["trade_date"],
            theme_id=payload["theme_id"],
            lifecycle_stage=payload["lifecycle_stage"],
            summary=payload.get("summary", ""),
            score_breakdown=payload.get("score_breakdown", {}),
            missing_metrics=payload.get("missing_metrics", []),
        )
        if existing is None:
            self.session.add(row)
        for key, value in payload.items():
            if key in ("trade_date", "theme_id"):
                continue
            setattr(row, key, value)
        await self.session.flush()
        return row

    async def upsert_sector_snapshots(self, rows: list[dict[str, Any]]) -> int:
        for payload in rows:
            await self.upsert_sector_snapshot(payload)
        return len(rows)

    async def upsert_candidate(self, payload: dict[str, Any]) -> ShortTermCandidate:
        existing = await self.session.scalar(
            select(ShortTermCandidate).where(
                ShortTermCandidate.trade_date == payload["trade_date"],
                ShortTermCandidate.strategy == payload["strategy"],
                ShortTermCandidate.stock_id == payload["stock_id"],
            )
        )
        row = existing or ShortTermCandidate(
            trade_date=payload["trade_date"],
            strategy=payload["strategy"],
            stock_id=payload["stock_id"],
            decision=payload.get("decision", "candidate"),
        )
        if existing is None:
            self.session.add(row)
        for key, value in payload.items():
            if key in ("trade_date", "strategy", "stock_id"):
                continue
            setattr(row, key, value)
        await self.session.flush()
        return row

    async def upsert_candidates(self, rows: list[dict[str, Any]]) -> int:
        for payload in rows:
            await self.upsert_candidate(payload)
        return len(rows)

    async def list_signals(
        self, trade_date: date, theme_id: int | None = None
    ) -> list[DailyStockSignal]:
        stmt = select(DailyStockSignal).where(DailyStockSignal.trade_date == trade_date)
        if theme_id is not None:
            stmt = stmt.where(DailyStockSignal.theme_id == theme_id)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_snapshots(self, trade_date: date) -> list[SectorRotationSnapshot]:
        result = await self.session.scalars(
            select(SectorRotationSnapshot)
            .where(SectorRotationSnapshot.trade_date == trade_date)
            .order_by(SectorRotationSnapshot.mainline_score.desc())
        )
        return list(result.all())

    async def list_lifecycle_history(
        self, theme_id: int, days: int = 10
    ) -> list[SectorRotationSnapshot]:
        result = await self.session.scalars(
            select(SectorRotationSnapshot)
            .where(SectorRotationSnapshot.theme_id == theme_id)
            .order_by(SectorRotationSnapshot.trade_date.desc())
            .limit(days)
        )
        rows = list(result.all())
        rows.reverse()
        return rows

    async def get_candidates(
        self, trade_date: date, strategy: str = "first_to_second"
    ) -> list[ShortTermCandidate]:
        result = await self.session.scalars(
            select(ShortTermCandidate)
            .where(
                ShortTermCandidate.trade_date == trade_date,
                ShortTermCandidate.strategy == strategy,
            )
            .order_by(ShortTermCandidate.rank.asc())
        )
        return list(result.all())
