"""数据模型单元测试

测试模型定义、字段验证、索引和软删除功能。
"""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import JSON

from app.models import Event, IndustryChain, Stock, Theme, ThemeStock


class TestThemeModel:
    """Theme 模型测试"""

    def test_theme_creation(self):
        """测试 Theme 模型创建"""
        theme = Theme(
            name="人工智能",
            code="AI",
            description="AI 相关题材",
            heat_index=Decimal("95.50"),
            rise_fall_pct=Decimal("2.35"),
            stock_count=50,
            category="科技",
            tags={"keywords": ["AI", "机器学习"]},
            source="东方财富",
        )
        assert theme.name == "人工智能"
        assert theme.code == "AI"
        assert theme.heat_index == Decimal("95.50")
        assert theme.stock_count == 50
        assert theme.tags == {"keywords": ["AI", "机器学习"]}

    def test_theme_default_values(self):
        """测试 Theme 默认值"""
        theme = Theme(name="测试", code="TEST")
        # 注意：Python 对象创建时不会自动应用 server_default
        # 默认值在数据库插入时由 server_default 应用
        assert theme.deleted_at is None
        assert theme.is_deleted is False

    def test_theme_soft_delete(self):
        """测试 Theme 软删除功能"""
        theme = Theme(name="测试", code="TEST")
        assert theme.is_deleted is False
        assert theme.deleted_at is None

        theme.soft_delete()
        assert theme.is_deleted is True
        assert theme.deleted_at is not None
        assert isinstance(theme.deleted_at, datetime)

    def test_theme_restore(self):
        """测试 Theme 恢复功能"""
        theme = Theme(name="测试", code="TEST")
        theme.soft_delete()
        assert theme.is_deleted is True

        theme.restore()
        assert theme.is_deleted is False
        assert theme.deleted_at is None

    def test_theme_indexes(self):
        """测试 Theme 索引定义"""
        indexes = {idx.name for idx in Theme.__table__.indexes}
        assert "idx_theme_name" in indexes
        assert "idx_theme_heat_index" in indexes

    def test_theme_columns(self):
        """测试 Theme 列定义"""
        columns = {c.name for c in Theme.__table__.columns}
        expected_columns = {
            "id", "name", "code", "description", "heat_index",
            "rise_fall_pct", "stock_count", "category", "tags",
            "source", "created_at", "updated_at", "deleted_at"
        }
        assert expected_columns == columns

    def test_tags_use_portable_json_type(self):
        assert isinstance(Theme.__table__.c.tags.type, JSON)

    def test_theme_repr(self):
        """测试 Theme 字符串表示"""
        theme = Theme(id=1, name="人工智能", code="AI")
        assert repr(theme) == "<Theme(id=1, name='人工智能', code='AI')>"


class TestStockModel:
    """Stock 模型测试"""

    def test_stock_creation(self):
        """测试 Stock 模型创建"""
        stock = Stock(
            code="600519",
            name="贵州茅台",
            industry="白酒",
            market_cap=Decimal("2000000000000.00"),
            current_price=Decimal("1800.50"),
            rise_fall_pct=Decimal("1.25"),
            exchange="SH",
        )
        assert stock.code == "600519"
        assert stock.name == "贵州茅台"
        assert stock.industry == "白酒"
        assert stock.exchange == "SH"

    def test_stock_indexes(self):
        """测试 Stock 索引定义"""
        indexes = {idx.name for idx in Stock.__table__.indexes}
        # code 字段有 UNIQUE 约束，MySQL 自动创建索引
        assert "idx_stock_name" in indexes

    def test_stock_columns(self):
        """测试 Stock 列定义"""
        columns = {c.name for c in Stock.__table__.columns}
        expected_columns = {
            "id", "code", "name", "industry", "market_cap",
            "current_price", "rise_fall_pct", "exchange",
            "created_at", "updated_at"
        }
        assert expected_columns == columns


class TestEventModel:
    """Event 模型测试"""

    def test_event_creation(self):
        """测试 Event 模型创建"""
        event = Event(
            title="茅台发布年报",
            content="内容详情",
            source="上交所",
            event_type="公告",
            published_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
            stock_id=1,
        )
        assert event.title == "茅台发布年报"
        assert event.stock_id == 1

    def test_event_indexes(self):
        """测试 Event 索引定义"""
        indexes = {idx.name for idx in Event.__table__.indexes}
        assert "idx_event_stock_id" in indexes
        assert "idx_event_published_at" in indexes


class TestIndustryChainModel:
    """IndustryChain 模型测试"""

    def test_industry_chain_creation(self):
        """测试 IndustryChain 模型创建"""
        chain = IndustryChain(
            theme_id=1,
            level="upstream",
            name="芯片设计",
            description="上游芯片设计环节",
            representative_companies=["华为海思", "寒武纪"],
            sort_order=1,
        )
        assert chain.theme_id == 1
        assert chain.level == "upstream"
        assert chain.name == "芯片设计"

    def test_industry_chain_indexes(self):
        """测试 IndustryChain 索引定义"""
        indexes = {idx.name for idx in IndustryChain.__table__.indexes}
        assert "idx_industry_chain_theme_id" in indexes

    def test_representative_companies_use_portable_json_type(self):
        column_type = IndustryChain.__table__.c.representative_companies.type
        assert isinstance(column_type, JSON)

    def test_industry_chain_check_constraint(self):
        """测试 IndustryChain.level 的 CHECK 约束"""
        # 验证 CheckConstraint 存在
        constraints = IndustryChain.__table__.constraints
        check_constraints = [c for c in constraints if hasattr(c, 'sqltext')]
        assert len(check_constraints) > 0


class TestThemeStockModel:
    """ThemeStock 关联表测试"""

    def test_theme_stock_creation(self):
        """测试 ThemeStock 关联表创建"""
        theme_stock = ThemeStock(
            theme_id=1,
            stock_id=1,
            chain_level="upstream",
            sort_order=1,
        )
        assert theme_stock.theme_id == 1
        assert theme_stock.stock_id == 1

    def test_theme_stock_composite_primary_key(self):
        """测试 ThemeStock 复合主键"""
        pk_columns = [c.name for c in ThemeStock.__table__.primary_key.columns]
        assert "theme_id" in pk_columns
        assert "stock_id" in pk_columns

    def test_theme_stock_indexes(self):
        """测试 ThemeStock 索引定义"""
        indexes = {idx.name for idx in ThemeStock.__table__.indexes}
        assert "idx_theme_stocks_stock_id" in indexes


class TestModelRelationships:
    """模型关系测试"""

    def test_theme_has_stocks_relationship(self):
        """测试 Theme 有 stocks 关系"""
        assert hasattr(Theme, 'stocks')

    def test_theme_has_industry_chains_relationship(self):
        """测试 Theme 有 industry_chains 关系"""
        assert hasattr(Theme, 'industry_chains')

    def test_stock_has_themes_relationship(self):
        """测试 Stock 有 themes 关系"""
        assert hasattr(Stock, 'themes')

    def test_stock_has_events_relationship(self):
        """测试 Stock 有 events 关系"""
        assert hasattr(Stock, 'events')

    def test_event_has_stock_relationship(self):
        """测试 Event 有 stock 关系"""
        assert hasattr(Event, 'stock')

    def test_industry_chain_has_theme_relationship(self):
        """测试 IndustryChain 有 theme 关系"""
        assert hasattr(IndustryChain, 'theme')


class TestTimestampMixin:
    """TimestampMixin 测试"""

    def test_all_models_have_timestamps(self):
        """测试所有模型都有时间戳字段"""
        models = [Theme, Stock, Event, IndustryChain, ThemeStock]
        for model in models:
            columns = {c.name for c in model.__table__.columns}
            assert "created_at" in columns, f"{model.__name__} missing created_at"
            assert "updated_at" in columns, f"{model.__name__} missing updated_at"
