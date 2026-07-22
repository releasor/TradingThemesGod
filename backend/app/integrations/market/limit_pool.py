"""AKShare 当日涨停池和跌停池适配器。"""

import asyncio
from collections.abc import Callable
from datetime import date

import akshare as ak
import pandas as pd

from app.core.logging import get_logger
from app.domain.theme_insights import normalize_stock_code

logger = get_logger(__name__)
PoolFetcher = Callable[..., pd.DataFrame]


class LimitPoolProvider:
    def __init__(
        self,
        limit_up_fetcher: PoolFetcher = ak.stock_zt_pool_em,
        limit_down_fetcher: PoolFetcher = ak.stock_zt_pool_dtgc_em,
    ):
        self.limit_up_fetcher = limit_up_fetcher
        self.limit_down_fetcher = limit_down_fetcher

    @staticmethod
    async def _fetch(
        fetcher: PoolFetcher, trade_date: str, pool_name: str
    ) -> set[str] | None:
        try:
            frame = await asyncio.to_thread(fetcher, date=trade_date)
            if "代码" not in frame.columns:
                logger.warning("limit_pool_missing_code", pool=pool_name)
                return None
            return {normalize_stock_code(value) for value in frame["代码"].tolist()}
        except Exception as exc:
            logger.warning("limit_pool_failed", pool=pool_name, error=str(exc))
            return None

    async def fetch(self, trade_date: date) -> tuple[set[str] | None, set[str] | None]:
        value = trade_date.strftime("%Y%m%d")
        limit_up, limit_down = await asyncio.gather(
            self._fetch(self.limit_up_fetcher, value, "limit_up"),
            self._fetch(self.limit_down_fetcher, value, "limit_down"),
        )
        return limit_up, limit_down
