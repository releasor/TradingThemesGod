"""个股 AI 研判报告仓储。"""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_ai_report import StockAiReport


class StockAiReportRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: int, stock_code: str) -> StockAiReport | None:
        return await self.session.scalar(
            select(StockAiReport).where(
                StockAiReport.user_id == user_id,
                StockAiReport.stock_code == stock_code,
            )
        )

    async def upsert(
        self,
        *,
        user_id: int,
        stock_code: str,
        stock_name: str | None,
        verdict: str,
        horizon_short: str,
        horizon_swing: str,
        horizon_medium_long: str,
        confidence: int,
        summary: str,
        sections: dict[str, Any],
        full_report: str,
        context_digest: dict[str, Any],
        model_provider_id: int | None,
        model_name: str | None,
        elapsed_ms: int,
        generated_at: datetime,
    ) -> StockAiReport:
        row = await self.get(user_id, stock_code)
        if row is None:
            row = StockAiReport(
                user_id=user_id,
                stock_code=stock_code,
            )
            self.session.add(row)

        row.stock_name = stock_name
        row.verdict = verdict
        row.horizon_short = horizon_short
        row.horizon_swing = horizon_swing
        row.horizon_medium_long = horizon_medium_long
        row.confidence = confidence
        row.summary = summary
        row.sections = sections
        row.full_report = full_report
        row.context_digest = context_digest
        row.model_provider_id = model_provider_id
        row.model_name = model_name
        row.elapsed_ms = elapsed_ms
        row.generated_at = generated_at
        await self.session.flush()
        return row
