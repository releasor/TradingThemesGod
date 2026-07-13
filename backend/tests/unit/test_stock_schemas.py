"""股票和事件 Schema 测试

验证 Pydantic 模型的正确性。
"""

from datetime import datetime, timezone
from decimal import Decimal

from app.schemas.stock import (
    StockBrief,
    StockDetailResponse,
    StockListResponse,
    EventBrief,
    EventListResponse,
)


class TestStockBrief:
    """StockBrief 模型测试"""

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "id": 1,
            "code": "600000",
            "name": "浦发银行",
            "industry": "银行",
            "market_cap": Decimal("1000000.00"),
            "current_price": Decimal("10.50"),
            "rise_fall_pct": Decimal("1.25"),
            "exchange": "SH",
        }
        brief = StockBrief(**data)
        assert brief.id == 1
        assert brief.code == "600000"
        assert brief.name == "浦发银行"
        assert brief.industry == "银行"
        assert brief.exchange == "SH"

    def test_optional_fields_none(self):
        """测试可选字段为 None"""
        data = {"id": 1, "code": "600000", "name": "浦发银行"}
        brief = StockBrief(**data)
        assert brief.industry is None
        assert brief.market_cap is None
        assert brief.current_price is None
        assert brief.rise_fall_pct is None
        assert brief.exchange is None


class TestEventBrief:
    """EventBrief 模型测试"""

    def test_from_dict(self):
        """测试从字典创建"""
        now = datetime.now(timezone.utc)
        data = {
            "id": 1,
            "title": "浦发银行发布年报",
            "content": "详细内容",
            "source": "东方财富",
            "event_type": "公告",
            "published_at": now,
        }
        brief = EventBrief(**data)
        assert brief.id == 1
        assert brief.title == "浦发银行发布年报"
        assert brief.published_at == now

    def test_optional_fields_none(self):
        """测试可选字段为 None"""
        data = {"id": 1, "title": "测试事件"}
        brief = EventBrief(**data)
        assert brief.content is None
        assert brief.source is None
        assert brief.event_type is None
        assert brief.published_at is None


class TestStockListResponse:
    """StockListResponse 模型测试"""

    def test_response_structure(self):
        """测试响应结构"""
        response = StockListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        assert response.items == []
        assert response.total == 0
        assert response.page == 1
        assert response.page_size == 20
        assert response.total_pages == 0

    def test_with_items(self):
        """测试包含数据的响应"""
        brief = StockBrief(id=1, code="600000", name="浦发银行")
        response = StockListResponse(
            items=[brief],
            total=1,
            page=1,
            page_size=20,
            total_pages=1,
        )
        assert len(response.items) == 1
        assert response.total == 1
        assert response.total_pages == 1


class TestStockDetailResponse:
    """StockDetailResponse 模型测试"""

    def test_response_structure(self):
        """测试响应结构"""
        now = datetime.now(timezone.utc)
        response = StockDetailResponse(
            id=1,
            code="600000",
            name="浦发银行",
            industry="银行",
            market_cap=Decimal("1000000.00"),
            current_price=Decimal("10.50"),
            rise_fall_pct=Decimal("1.25"),
            exchange="SH",
            created_at=now,
            updated_at=now,
            recent_events=[],
        )
        assert response.id == 1
        assert response.code == "600000"
        assert response.recent_events == []

    def test_with_events(self):
        """测试包含事件的响应"""
        now = datetime.now(timezone.utc)
        event = EventBrief(id=1, title="测试事件", published_at=now)
        response = StockDetailResponse(
            id=1,
            code="600000",
            name="浦发银行",
            created_at=now,
            updated_at=now,
            recent_events=[event],
        )
        assert len(response.recent_events) == 1
        assert response.recent_events[0].title == "测试事件"


class TestEventListResponse:
    """EventListResponse 模型测试"""

    def test_response_structure(self):
        """测试响应结构"""
        response = EventListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        assert response.items == []
        assert response.total == 0
