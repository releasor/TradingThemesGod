"""Pydantic Schema 单元测试

测试数据验证、序列化和工具函数。
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from pydantic import ValidationError

from app.schemas.common import calculate_total_pages
from app.schemas.scraper import ScraperRunRequest
from app.schemas.theme import (
    ThemeSearchParams,
    ThemeBrief,
    ThemeListResponse,
    ThemeDetailResponse,
    ThemeRankingResponse,
    ThemeCategoriesResponse,
    IndustryChainBrief,
)
from app.schemas.stock import (
    StockBrief,
    StockDetailResponse,
    EventListItem,
    EventListResponse,
    StockListResponse,
)


class TestCalculateTotalPages:
    """calculate_total_pages 函数测试"""

    def test_normal_division(self):
        """测试正常除法"""
        assert calculate_total_pages(100, 20) == 5

    def test_rounds_up(self):
        """测试向上取整"""
        assert calculate_total_pages(101, 20) == 6
        assert calculate_total_pages(1, 20) == 1

    def test_zero_total(self):
        """测试总数为零返回零页"""
        assert calculate_total_pages(0, 20) == 0

    def test_exact_division(self):
        """测试整除"""
        assert calculate_total_pages(40, 20) == 2

    def test_single_item(self):
        """测试单条数据"""
        assert calculate_total_pages(1, 1) == 1

    def test_large_numbers(self):
        """测试大数"""
        assert calculate_total_pages(10000, 50) == 200
class TestThemeSearchParams:
    """ThemeSearchParams 验证测试"""

    def test_default_values(self):
        """测试默认值"""
        params = ThemeSearchParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort_by == "heat_index"
        assert params.sort_order == "desc"
        assert params.category is None
        assert params.tags is None

    def test_valid_custom_values(self):
        """测试有效的自定义值"""
        params = ThemeSearchParams(
            page=2,
            page_size=50,
            sort_by="name",
            sort_order="asc",
            category="科技",
            tags="AI,机器学习",
        )
        assert params.page == 2
        assert params.page_size == 50
        assert params.sort_by == "name"
        assert params.sort_order == "asc"
        assert params.category == "科技"

    def test_page_must_be_positive(self):
        """测试页码必须为正数"""
        with pytest.raises(ValidationError):
            ThemeSearchParams(page=0)

    def test_page_size_range(self):
        """测试每页数量范围"""
        # 最小值
        params = ThemeSearchParams(page_size=1)
        assert params.page_size == 1
        # 最大值
        params = ThemeSearchParams(page_size=100)
        assert params.page_size == 100
        # 超过最大值
        with pytest.raises(ValidationError):
            ThemeSearchParams(page_size=101)

    def test_sort_by_valid_values(self):
        """测试排序字段有效值"""
        for field in ["heat_index", "rise_fall_pct", "stock_count", "name"]:
            params = ThemeSearchParams(sort_by=field)
            assert params.sort_by == field

    def test_sort_by_invalid_value(self):
        """测试排序字段无效值"""
        with pytest.raises(ValidationError):
            ThemeSearchParams(sort_by="invalid_field")

    def test_sort_order_valid_values(self):
        """测试排序方向有效值"""
        assert ThemeSearchParams(sort_order="asc").sort_order == "asc"
        assert ThemeSearchParams(sort_order="desc").sort_order == "desc"

    def test_sort_order_invalid_value(self):
        """测试排序方向无效值"""
        with pytest.raises(ValidationError):
            ThemeSearchParams(sort_order="random")

    def test_tags_max_count(self):
        """测试标签最大数量限制"""
        # 10 个标签应该通过
        tags = ",".join([f"tag{i}" for i in range(10)])
        params = ThemeSearchParams(tags=tags)
        assert params.tags == tags

    def test_tags_too_many(self):
        """测试超过10个标签"""
        tags = ",".join([f"tag{i}" for i in range(11)])
        with pytest.raises(ValidationError, match="最多支持10个标签"):
            ThemeSearchParams(tags=tags)

    def test_tag_too_long(self):
        """测试单个标签超过20字符"""
        long_tag = "a" * 21
        with pytest.raises(ValidationError, match="单个标签长度"):
            ThemeSearchParams(tags=long_tag)

    def test_tags_with_empty_segments(self):
        """测试带空段的标签"""
        params = ThemeSearchParams(tags="AI,,机器学习, ")
        # 空段应该被过滤，不计入标签数量
        assert params.tags == "AI,,机器学习, "
class TestStockDetailResponse:
    """StockDetailResponse 验证测试"""

    def test_valid_stock_code(self):
        """测试有效的股票代码"""
        data = {
            "id": 1,
            "code": "600519",
            "name": "贵州茅台",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "recent_events": [],
        }
        resp = StockDetailResponse(**data)
        assert resp.code == "600519"

    def test_invalid_stock_code_letters(self):
        """测试无效股票代码（含字母）"""
        data = {
            "id": 1,
            "code": "abcdef",
            "name": "测试",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "recent_events": [],
        }
        with pytest.raises(ValidationError, match="6位数字"):
            StockDetailResponse(**data)

    def test_invalid_stock_code_short(self):
        """测试无效股票代码（太短）"""
        data = {
            "id": 1,
            "code": "6005",
            "name": "测试",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "recent_events": [],
        }
        with pytest.raises(ValidationError, match="6位数字"):
            StockDetailResponse(**data)

    def test_invalid_stock_code_long(self):
        """测试无效股票代码（太长）"""
        data = {
            "id": 1,
            "code": "6005190",
            "name": "测试",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "recent_events": [],
        }
        with pytest.raises(ValidationError, match="6位数字"):
            StockDetailResponse(**data)

    def test_optional_fields(self):
        """测试可选字段"""
        data = {
            "id": 1,
            "code": "600519",
            "name": "贵州茅台",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "recent_events": [],
        }
        resp = StockDetailResponse(**data)
        assert resp.industry is None
        assert resp.market_cap is None
        assert resp.current_price is None
        assert resp.rise_fall_pct is None
        assert resp.exchange is None

    def test_with_all_fields(self):
        """测试包含所有字段"""
        now = datetime.now(timezone.utc)
        data = {
            "id": 1,
            "code": "600519",
            "name": "贵州茅台",
            "industry": "白酒",
            "market_cap": Decimal("2000000000000"),
            "current_price": Decimal("1800.50"),
            "rise_fall_pct": Decimal("1.25"),
            "exchange": "SH",
            "created_at": now,
            "updated_at": now,
            "recent_events": [
                EventListItem(id=1, title="发布年报", source="上交所", event_type="公告", published_at=now),
            ],
        }
        resp = StockDetailResponse(**data)
        assert resp.industry == "白酒"
        assert resp.market_cap == Decimal("2000000000000")
        assert len(resp.recent_events) == 1
        assert resp.recent_events[0].title == "发布年报"
class TestThemeBrief:
    """ThemeBrief 模型测试"""

    def test_create_theme_brief(self):
        """测试创建 ThemeBrief"""
        data = {
            "id": 1,
            "name": "人工智能",
            "code": "AI",
            "heat_index": Decimal("95.50"),
            "rise_fall_pct": Decimal("2.35"),
            "stock_count": 50,
        }
        brief = ThemeBrief(**data)
        assert brief.id == 1
        assert brief.name == "人工智能"
        assert brief.description is None
        assert brief.category is None
        assert brief.source is None

    def test_create_with_all_fields(self):
        """测试包含所有字段"""
        data = {
            "id": 1,
            "name": "人工智能",
            "code": "AI",
            "description": "AI相关题材",
            "heat_index": Decimal("95.50"),
            "rise_fall_pct": Decimal("2.35"),
            "stock_count": 50,
            "category": "科技",
            "tags": {"keywords": ["AI"]},
            "source": "东方财富",
        }
        brief = ThemeBrief(**data)
        assert brief.description == "AI相关题材"
        assert brief.category == "科技"
        assert brief.source == "东方财富"


class TestIndustryChainBrief:
    """IndustryChainBrief 模型测试"""

    def test_create_industry_chain_brief(self):
        """测试创建 IndustryChainBrief"""
        data = {
            "id": 1,
            "level": "upstream",
            "name": "芯片设计",
            "sort_order": 1,
        }
        brief = IndustryChainBrief(**data)
        assert brief.id == 1
        assert brief.level == "upstream"
        assert brief.name == "芯片设计"
        assert brief.description is None
        assert brief.representative_companies is None


class TestThemeListResponse:
    """ThemeListResponse 模型测试"""

    def test_create_response(self):
        """测试创建列表响应"""
        data = {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "total_pages": 0,
        }
        resp = ThemeListResponse(**data)
        assert resp.items == []
        assert resp.total == 0
        assert resp.total_pages == 0


class TestThemeCategoriesResponse:
    """ThemeCategoriesResponse 模型测试"""

    def test_create_categories(self):
        """测试创建分类响应"""
        resp = ThemeCategoriesResponse(categories=["科技", "能源", "医疗"])
        assert len(resp.categories) == 3
        assert "科技" in resp.categories

    def test_empty_categories(self):
        """测试空分类"""
        resp = ThemeCategoriesResponse(categories=[])
        assert resp.categories == []


class TestThemeRankingResponse:
    """ThemeRankingResponse 模型测试"""

    def test_create_ranking(self):
        """测试创建排名响应"""
        resp = ThemeRankingResponse(items=[], limit=20)
        assert resp.items == []
        assert resp.limit == 20


class TestEventListItem:
    """EventListItem 模型测试"""

    def test_create_event_list_item(self):
        """测试创建事件列表项"""
        now = datetime.now(timezone.utc)
        item = EventListItem(
            id=1,
            title="茅台发布年报",
            source="上交所",
            event_type="公告",
            published_at=now,
        )
        assert item.id == 1
        assert item.title == "茅台发布年报"


class TestStockBrief:
    """StockBrief 模型测试"""

    def test_create_stock_brief(self):
        """测试创建股票简要信息"""
        data = {
            "id": 1,
            "code": "600519",
            "name": "贵州茅台",
        }
        brief = StockBrief(**data)
        assert brief.id == 1
        assert brief.code == "600519"
        assert brief.industry is None
        assert brief.market_cap is None

    def test_create_with_all_fields(self):
        """测试包含所有字段"""
        data = {
            "id": 1,
            "code": "600519",
            "name": "贵州茅台",
            "industry": "白酒",
            "market_cap": Decimal("2000000000000"),
            "current_price": Decimal("1800.50"),
            "rise_fall_pct": Decimal("1.25"),
            "exchange": "SH",
        }
        brief = StockBrief(**data)
        assert brief.industry == "白酒"
        assert brief.exchange == "SH"


class TestScraperRunRequest:
    """ScraperRunRequest 验证测试"""

    def test_default_empty_params(self):
        """测试默认空参数"""
        req = ScraperRunRequest()
        assert req.params == {}

    def test_valid_params(self):
        """测试有效参数"""
        req = ScraperRunRequest(params={"url": "http://example.com", "limit": "10"})
        assert req.params["url"] == "http://example.com"
        assert req.params["limit"] == "10"

    def test_max_20_params(self):
        """测试最多20个参数"""
        params = {f"key{i}": f"value{i}" for i in range(20)}
        req = ScraperRunRequest(params=params)
        assert len(req.params) == 20

    def test_more_than_20_params_fails(self):
        """测试超过20个参数失败"""
        params = {f"key{i}": f"value{i}" for i in range(21)}
        with pytest.raises(ValidationError, match="参数数量不能超过20个"):
            ScraperRunRequest(params=params)

    def test_key_too_long_fails(self):
        """测试参数名过长失败"""
        long_key = "a" * 51
        with pytest.raises(ValidationError, match="参数名必须是字符串且长度不超过50"):
            ScraperRunRequest(params={long_key: "value"})

    def test_string_value_too_long_fails(self):
        """测试字符串值过长失败"""
        long_value = "a" * 501
        with pytest.raises(ValidationError, match="值长度不能超过500"):
            ScraperRunRequest(params={"key": long_value})

    def test_non_string_values_accepted(self):
        """测试非字符串值被接受"""
        req = ScraperRunRequest(params={"count": 100, "tags": ["a", "b"], "meta": {"x": 1}, "empty": None})
        assert req.params["count"] == 100
        assert req.params["tags"] == ["a", "b"]
        assert req.params["meta"] == {"x": 1}
        assert req.params["empty"] is None

    def test_empty_dict_valid(self):
        """测试空字典有效"""
        req = ScraperRunRequest(params={})
        assert req.params == {}
