"""StockRepository 和 EventRepository 单元测试

测试股票和事件仓储的数据库查询操作。
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.models.stock import Stock
from app.models.event import Event
from app.repositories.stock import StockRepository, EventRepository


@pytest.fixture
def mock_session():
    """创建模拟的 AsyncSession"""
    session = AsyncMock()
    return session


@pytest.fixture
def sample_stocks():
    """示例股票数据"""
    return [
        Stock(
            id=1,
            code="600519",
            name="贵州茅台",
            industry="白酒",
            market_cap=Decimal("21000.00"),
            current_price=Decimal("1680.00"),
            rise_fall_pct=Decimal("1.25"),
            exchange="SH",
        ),
        Stock(
            id=2,
            code="000858",
            name="五粮液",
            industry="白酒",
            market_cap=Decimal("8000.00"),
            current_price=Decimal("155.50"),
            rise_fall_pct=Decimal("-0.80"),
            exchange="SZ",
        ),
        Stock(
            id=3,
            code="300750",
            name="宁德时代",
            industry="电池",
            market_cap=Decimal("10000.00"),
            current_price=Decimal("210.00"),
            rise_fall_pct=Decimal("3.10"),
            exchange="SZ",
        ),
    ]


@pytest.fixture
def sample_events():
    """示例事件数据"""
    return [
        Event(
            id=1,
            title="贵州茅台发布年报",
            content="净利润同比增长15%",
            source="东方财富",
            event_type="公告",
            published_at=datetime(2025, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
            stock_id=1,
        ),
        Event(
            id=2,
            title="白酒板块集体上涨",
            content=None,
            source="同花顺",
            event_type="行情",
            published_at=datetime(2025, 3, 14, 14, 30, 0, tzinfo=timezone.utc),
            stock_id=1,
        ),
    ]


class TestStockRepository:
    """StockRepository 测试"""

    def test_init(self, mock_session):
        """测试初始化"""
        repo = StockRepository(mock_session)
        assert repo.session is mock_session

    @pytest.mark.asyncio
    async def test_list_paginated_basic(self, mock_session, sample_stocks):
        """测试基本分页查询"""
        repo = StockRepository(mock_session)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 3

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = sample_stocks

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        stocks, total = await repo.list_paginated(page=1, page_size=20)

        assert total == 3
        assert len(stocks) == 3
        assert stocks[0].code == "600519"

    @pytest.mark.asyncio
    async def test_list_paginated_industry_filter(self, mock_session, sample_stocks):
        """测试按行业筛选"""
        repo = StockRepository(mock_session)

        baijiu_stocks = [s for s in sample_stocks if s.industry == "白酒"]

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = baijiu_stocks

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        stocks, total = await repo.list_paginated(page=1, page_size=20, industry="白酒")

        assert total == 2
        assert all(s.industry == "白酒" for s in stocks)

    @pytest.mark.asyncio
    async def test_list_paginated_exchange_filter(self, mock_session, sample_stocks):
        """测试按交易所筛选"""
        repo = StockRepository(mock_session)

        sz_stocks = [s for s in sample_stocks if s.exchange == "SZ"]

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = sz_stocks

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        stocks, total = await repo.list_paginated(page=1, page_size=20, exchange="SZ")

        assert total == 2
        assert all(s.exchange == "SZ" for s in stocks)

    @pytest.mark.asyncio
    async def test_list_paginated_sort_by_name(self, mock_session, sample_stocks):
        """测试按名称排序"""
        repo = StockRepository(mock_session)

        sorted_stocks = sorted(sample_stocks, key=lambda s: s.name)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 3

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = sorted_stocks

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        stocks, total = await repo.list_paginated(
            page=1, page_size=20, sort_by="name", order="asc"
        )

        assert total == 3
        assert stocks[0].name <= stocks[1].name

    @pytest.mark.asyncio
    async def test_list_paginated_invalid_sort_field(self, mock_session, sample_stocks):
        """测试无效排序字段回退到默认(code)"""
        repo = StockRepository(mock_session)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 3

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = sample_stocks

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        # invalid_field 不在白名单中，应回退到 code
        stocks, total = await repo.list_paginated(
            page=1, page_size=20, sort_by="invalid_field"
        )

        assert total == 3
        assert len(stocks) == 3

    @pytest.mark.asyncio
    async def test_list_paginated_empty_result(self, mock_session):
        """测试空结果"""
        repo = StockRepository(mock_session)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        stocks, total = await repo.list_paginated(page=1, page_size=20)

        assert total == 0
        assert len(stocks) == 0

    @pytest.mark.asyncio
    async def test_get_by_code_found(self, mock_session, sample_stocks):
        """测试按代码查询（找到）"""
        repo = StockRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_stocks[0]
        mock_session.execute.return_value = mock_result

        stock = await repo.get_by_code("600519")

        assert stock is not None
        assert stock.code == "600519"
        assert stock.name == "贵州茅台"

    @pytest.mark.asyncio
    async def test_get_by_code_not_found(self, mock_session):
        """测试按代码查询（未找到）"""
        repo = StockRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        stock = await repo.get_by_code("999999")

        assert stock is None

    @pytest.mark.asyncio
    async def test_exists_by_code_true(self, mock_session):
        """测试股票存在检查（存在）"""
        repo = StockRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1
        mock_session.execute.return_value = mock_result

        exists = await repo.exists_by_code("600519")

        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_by_code_false(self, mock_session):
        """测试股票存在检查（不存在）"""
        repo = StockRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        exists = await repo.exists_by_code("999999")

        assert exists is False

    @pytest.mark.asyncio
    async def test_get_events_by_code_found(self, mock_session, sample_events):
        """测试获取股票事件（找到股票和事件）"""
        repo = StockRepository(mock_session)

        # 第一次 execute: 查找股票 ID
        mock_stock_result = MagicMock()
        mock_stock_result.scalar_one_or_none.return_value = 1

        # 第二次 execute: count 查询
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        # 第三次 execute: 数据查询
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = sample_events

        mock_session.execute.side_effect = [
            mock_stock_result,
            mock_count_result,
            mock_data_result,
        ]

        events, total, stock_exists = await repo.get_events_by_code("600519")

        assert stock_exists is True
        assert total == 2
        assert len(events) == 2
        assert events[0].title == "贵州茅台发布年报"

    @pytest.mark.asyncio
    async def test_get_events_by_code_stock_not_found(self, mock_session):
        """测试获取事件（股票不存在）"""
        repo = StockRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        events, total, stock_exists = await repo.get_events_by_code("999999")

        assert stock_exists is False
        assert total == 0
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_get_events_by_code_no_events(self, mock_session):
        """测试获取事件（股票存在但无事件）"""
        repo = StockRepository(mock_session)

        # 第一次 execute: 查找股票 ID
        mock_stock_result = MagicMock()
        mock_stock_result.scalar_one_or_none.return_value = 1

        # 第二次 execute: count 查询
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        # 第三次 execute: 数据查询
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [
            mock_stock_result,
            mock_count_result,
            mock_data_result,
        ]

        events, total, stock_exists = await repo.get_events_by_code("600519")

        assert stock_exists is True
        assert total == 0
        assert len(events) == 0


class TestEventRepository:
    """EventRepository 测试"""

    def test_init(self, mock_session):
        """测试初始化"""
        repo = EventRepository(mock_session)
        assert repo.session is mock_session

    @pytest.mark.asyncio
    async def test_get_recent_by_stock_id_found(self, mock_session, sample_events):
        """测试获取最近事件（有事件）"""
        repo = EventRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_events
        mock_session.execute.return_value = mock_result

        events = await repo.get_recent_by_stock_id(stock_id=1, limit=5)

        assert len(events) == 2
        assert events[0].stock_id == 1

    @pytest.mark.asyncio
    async def test_get_recent_by_stock_id_empty(self, mock_session):
        """测试获取最近事件（无事件）"""
        repo = EventRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        events = await repo.get_recent_by_stock_id(stock_id=999, limit=5)

        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_list_paginated_basic(self, mock_session, sample_events):
        """测试基本分页查询"""
        repo = EventRepository(mock_session)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = sample_events

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        events, total = await repo.list_paginated(page=1, page_size=20)

        assert total == 2
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_list_paginated_event_type_filter(self, mock_session, sample_events):
        """测试按事件类型筛选"""
        repo = EventRepository(mock_session)

        announcement_events = [e for e in sample_events if e.event_type == "公告"]

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = announcement_events

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        events, total = await repo.list_paginated(
            page=1, page_size=20, event_type="公告"
        )

        assert total == 1
        assert events[0].event_type == "公告"

    @pytest.mark.asyncio
    async def test_list_paginated_invalid_sort_field(self, mock_session, sample_events):
        """测试无效排序字段回退到默认(published_at)"""
        repo = EventRepository(mock_session)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = sample_events

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        events, total = await repo.list_paginated(
            page=1, page_size=20, sort_by="invalid_field"
        )

        assert total == 2
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_list_paginated_empty_result(self, mock_session):
        """测试空结果"""
        repo = EventRepository(mock_session)

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        events, total = await repo.list_paginated(page=1, page_size=20)

        assert total == 0
        assert len(events) == 0
