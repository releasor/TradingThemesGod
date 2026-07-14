"""题材 Schema 测试

验证题材相关 Pydantic 模型的正确性。
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.theme import (
    ThemeBrief,
    ThemeSearchParams,
)


class TestThemeSearchParams:
    """ThemeSearchParams 模型测试"""

    def test_default_values(self):
        """测试默认参数值"""
        params = ThemeSearchParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort_by == "heat_index"
        assert params.sort_order == "desc"
        assert params.category is None
        assert params.tags is None

    def test_custom_values(self):
        """测试自定义参数值"""
        params = ThemeSearchParams(
            page=2,
            page_size=50,
            sort_by="rise_fall_pct",
            sort_order="asc",
            category="科技",
            tags="AI,半导体",
        )
        assert params.page == 2
        assert params.page_size == 50
        assert params.sort_by == "rise_fall_pct"
        assert params.sort_order == "asc"
        assert params.category == "科技"
        assert params.tags == "AI,半导体"

    def test_valid_tags_within_limit(self):
        """测试 10 个以内的标签通过验证"""
        tags = ",".join([f"tag{i}" for i in range(1, 11)])
        params = ThemeSearchParams(tags=tags)
        assert params.tags == tags

    def test_tags_exceed_max_count(self):
        """测试超过 10 个标签时验证失败"""
        tags = ",".join([f"tag{i}" for i in range(1, 12)])
        with pytest.raises(ValidationError) as exc_info:
            ThemeSearchParams(tags=tags)
        assert "最多支持10个标签筛选" in str(exc_info.value)

    def test_single_tag_max_length(self):
        """测试单个标签超过 20 字符时验证失败"""
        long_tag = "a" * 21
        with pytest.raises(ValidationError) as exc_info:
            ThemeSearchParams(tags=long_tag)
        assert "单个标签长度不能超过20个字符" in str(exc_info.value)

    def test_tags_exactly_20_chars(self):
        """测试单个标签恰好 20 字符时通过验证"""
        tag = "a" * 20
        params = ThemeSearchParams(tags=tag)
        assert params.tags == tag

    def test_invalid_sort_by_value(self):
        """测试无效的 sort_by 值"""
        with pytest.raises(ValidationError):
            ThemeSearchParams(sort_by="invalid_field")

    def test_invalid_sort_order_value(self):
        """测试无效的 sort_order 值"""
        with pytest.raises(ValidationError):
            ThemeSearchParams(sort_order="random")

    def test_page_must_be_positive(self):
        """测试页码必须 >= 1"""
        with pytest.raises(ValidationError):
            ThemeSearchParams(page=0)

    def test_page_size_range(self):
        """测试每页数量范围约束"""
        # 有效范围
        params = ThemeSearchParams(page_size=1)
        assert params.page_size == 1
        params = ThemeSearchParams(page_size=100)
        assert params.page_size == 100

        # 超出范围
        with pytest.raises(ValidationError):
            ThemeSearchParams(page_size=0)
        with pytest.raises(ValidationError):
            ThemeSearchParams(page_size=101)

    def test_tags_with_whitespace(self):
        """测试标签中含空格的处理"""
        params = ThemeSearchParams(tags=" AI , 半导体 ")
        # 验证不报错，空格被 strip 处理
        assert params.tags == " AI , 半导体 "

    def test_empty_tags_string_passes(self):
        """测试空标签字符串通过验证（validator 不拒绝）"""
        params = ThemeSearchParams(tags="")
        assert params.tags == ""


class TestThemeBrief:
    """ThemeBrief 模型测试"""

    def test_from_attributes(self):
        """测试从对象属性创建"""
        data = {
            "id": 1,
            "name": "人工智能",
            "code": "AI",
            "description": "AI 主题",
            "heat_index": Decimal("95.5"),
            "rise_fall_pct": Decimal("3.25"),
            "stock_count": 50,
            "category": "科技",
            "tags": ["AI", "机器学习"],
            "source": "东方财富",
        }
        brief = ThemeBrief(**data)
        assert brief.id == 1
        assert brief.name == "人工智能"
        assert brief.code == "AI"
        assert brief.description == "AI 主题"
        assert brief.heat_index == Decimal("95.5")
        assert brief.rise_fall_pct == Decimal("3.25")
        assert brief.stock_count == 50
        assert brief.category == "科技"
        assert brief.tags == ["AI", "机器学习"]
        assert brief.source == "东方财富"

    def test_optional_fields_none(self):
        """测试可选字段为 None"""
        data = {
            "id": 1,
            "name": "测试题材",
            "code": "TEST",
            "heat_index": Decimal("50.0"),
            "rise_fall_pct": Decimal("0"),
            "stock_count": 10,
        }
        brief = ThemeBrief(**data)
        assert brief.description is None
        assert brief.category is None
        assert brief.tags is None
        assert brief.source is None

    def test_from_attributes_config(self):
        """测试 from_attributes 配置允许从 ORM 对象构建"""
        # 模拟 ORM 对象
        class FakeORMTheme:
            id = 1
            name = "新能源"
            code = "NE"
            description = None
            heat_index = Decimal("80.0")
            rise_fall_pct = Decimal("-1.5")
            stock_count = 30
            category = "能源"
            tags = None
            source = None

        brief = ThemeBrief.model_validate(FakeORMTheme())
        assert brief.id == 1
        assert brief.name == "新能源"
        assert brief.code == "NE"

    def test_required_fields_missing(self):
        """测试缺少必填字段时验证失败"""
        with pytest.raises(ValidationError):
            ThemeBrief(id=1, name="test")
