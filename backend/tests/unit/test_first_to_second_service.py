"""一进二候选服务测试。"""

from datetime import date

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.first_to_second import FirstToSecondProvider, FirstToSecondService


class FakeProvider(FirstToSecondProvider):
    async def fetch_previous_first_limit_up(self, trade_date: date) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "代码": "000001",
                    "名称": "平安银行",
                    "最新价": 12.3,
                    "总市值": 12000000000,
                    "流通市值": 6000000000,
                    "换手率": 8.5,
                    "成交额": 920000000,
                    "首次封板时间": "09:42:00",
                    "开板次数": 0,
                    "连续涨停": 1,
                    "是否一字板": False,
                    "是否炸板": False,
                    "所属行业": "金融科技",
                },
                {
                    "代码": "000002",
                    "名称": "高价股份",
                    "最新价": 31.2,
                    "总市值": 9000000000,
                    "流通市值": 5000000000,
                    "换手率": 7.2,
                    "成交额": 510000000,
                    "首次封板时间": "09:35:00",
                    "开板次数": 0,
                    "连续涨停": 1,
                    "是否一字板": False,
                    "是否炸板": False,
                    "所属行业": "机器人",
                },
                {
                    "代码": "000003",
                    "名称": "一字股份",
                    "最新价": 10.2,
                    "总市值": 7000000000,
                    "流通市值": 4000000000,
                    "换手率": 1.1,
                    "成交额": 120000000,
                    "首次封板时间": "09:30:00",
                    "开板次数": 0,
                    "连续涨停": 1,
                    "是否一字板": True,
                    "是否炸板": False,
                    "所属行业": "机器人",
                },
            ]
        )

    async def fetch_today_limit_up(self, trade_date: date) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"代码": "000001", "名称": "平安银行"},
                {"代码": "000002", "名称": "高价股份"},
                {"代码": "000003", "名称": "一字股份"},
            ]
        )

    async def fetch_today_near_limit_up(self, trade_date: date) -> pd.DataFrame:
        return pd.DataFrame([])


@pytest.mark.asyncio
async def test_first_to_second_service_filters_and_scores_live_candidates():
    service = FirstToSecondService(session=AsyncSession(), provider=FakeProvider())

    response = await service.get_candidates(date(2026, 7, 21), force_refresh=True)

    assert response.trade_date == date(2026, 7, 21)
    assert response.previous_trade_date == date(2026, 7, 20)
    assert response.degraded is True
    assert "model_catalyst" in response.missing_sources
    assert response.excluded_count == 2
    assert [item.code for item in response.candidates] == ["000001"]

    candidate = response.candidates[0]
    assert candidate.score >= 80
    assert candidate.float_market_cap == 60
    assert candidate.market_cap == 120
    assert "今日仍在涨停池" in candidate.matched_rules
    assert "流通市值 20-80 亿" in candidate.matched_rules
    assert candidate.excluded_rules == []
    assert candidate.operation_advice.startswith("只做换手晋级确认")
