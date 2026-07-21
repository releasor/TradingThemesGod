# 题材详情研究信息与行情统计实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为每个题材详情页提供可追溯的结构化介绍、互联网驱动事件，以及最新涨跌停和涨跌家数统计。

**Architecture:** 使用三个独立 MySQL 持久化模型保存题材档案、驱动事件和每日市场快照。研究刷新服务复用现有网页搜索、财经新闻、反爬和模型适配器，行情服务把题材成分股与 AKShare 涨跌停池做集合聚合；题材详情服务统一读取三个模块，React 端使用三个聚焦组件展示并允许手动刷新研究资料。

**Tech Stack:** Python 3.12、FastAPI、SQLAlchemy Async、Alembic、MySQL 8.0、httpx、BeautifulSoup、AKShare、Pydantic v2、pytest、React 19、TypeScript、TanStack Query、Tailwind CSS、Vitest、Testing Library。

---

## 文件结构

### 新建文件

- `backend/alembic/versions/010_create_theme_insights.py`：创建三张题材洞察表及其约束。
- `backend/app/models/theme_profile.py`：题材结构化档案 ORM。
- `backend/app/models/theme_driver_event.py`：题材驱动事件 ORM。
- `backend/app/models/theme_market_snapshot.py`：题材每日行情快照 ORM。
- `backend/app/schemas/theme_insight.py`：持久化对象、刷新结果和模型抽取载荷的 Pydantic 契约。
- `backend/app/repositories/theme_insight.py`：题材档案、事件和快照的数据访问。
- `backend/app/domain/theme_insights.py`：URL 规范化、关键词降级、时间窗口和涨跌分类纯函数。
- `backend/app/integrations/market/limit_pool.py`：AKShare 涨停池/跌停池适配器。
- `backend/app/services/theme_market.py`：题材行情统计与每日快照写入。
- `backend/app/services/theme_insight.py`：公开资料采集、AI 抽取、降级和增量刷新编排。
- `backend/app/services/theme_insight_scheduler.py`：有界批量研究刷新周期任务。
- `backend/tests/unit/test_theme_insight_models.py`：模型和元数据约束测试。
- `backend/tests/unit/test_theme_insight_repository.py`：仓储查询与幂等写入测试。
- `backend/tests/unit/test_theme_insight_domain.py`：纯函数和降级逻辑测试。
- `backend/tests/unit/test_limit_pool.py`：第三方 DataFrame 适配测试。
- `backend/tests/unit/test_theme_market_service.py`：行情聚合测试。
- `backend/tests/unit/test_theme_insight_service.py`：研究刷新、AI 和降级测试。
- `backend/tests/unit/test_theme_insight_scheduler.py`：周期任务启动、停止、批量和异常隔离测试。
- `frontend/src/components/ThemeMarketBreadth.tsx`：涨跌停及涨跌家数展示。
- `frontend/src/components/ThemeMarketBreadth.test.tsx`：行情展示测试。
- `frontend/src/components/ThemeProfileSection.tsx`：结构化题材介绍与来源。
- `frontend/src/components/ThemeProfileSection.test.tsx`：介绍展示测试。
- `frontend/src/components/ThemeDriverEvents.tsx`：驱动事件时间线。
- `frontend/src/components/ThemeDriverEvents.test.tsx`：事件展示测试。

### 修改文件

- `backend/app/models/theme.py`、`backend/app/models/__init__.py`：注册三个模型关系。
- `backend/app/schemas/theme.py`：扩展题材详情响应。
- `backend/app/repositories/theme.py`：提供全部题材成分股行情查询。
- `backend/app/services/web_research.py`：接入反爬中间件并增加题材档案/事件搜索入口。
- `backend/app/services/theme.py`：聚合档案、事件和最新快照。
- `backend/app/api/theme.py`：新增研究刷新端点。
- `backend/app/core/config.py`、`backend/.env.example`：增加研究更新周期和开关。
- `backend/app/main.py`：启动和停止独立的题材研究周期任务。
- `backend/app/scrapers/eastmoney.py`：成分股行情成功写入后触发当日题材市场快照刷新。
- `backend/tests/unit/test_theme_schemas.py`、`backend/tests/unit/test_theme_service.py`、`backend/tests/integration/test_theme_api.py`、`backend/tests/unit/test_app_lifespan.py`：覆盖 API 聚合和生命周期。
- `frontend/src/types/theme.ts`、`frontend/src/api/theme.ts`、`frontend/src/api/theme.test.ts`：同步 API 契约并添加刷新函数。
- `frontend/src/features/themes/ThemeDetail.tsx`、`frontend/src/features/themes/ThemeDetail.test.tsx`：组合新组件和刷新状态。

## Task 1：建立持久化模型与迁移

**Files:**
- Create: `backend/alembic/versions/010_create_theme_insights.py`
- Create: `backend/app/models/theme_profile.py`
- Create: `backend/app/models/theme_driver_event.py`
- Create: `backend/app/models/theme_market_snapshot.py`
- Modify: `backend/app/models/theme.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/unit/test_theme_insight_models.py`

- [ ] **Step 1：先写失败的模型元数据测试**

```python
from app.models.theme_driver_event import ThemeDriverEvent
from app.models.theme_market_snapshot import ThemeMarketSnapshot
from app.models.theme_profile import ThemeProfile


def test_theme_profile_has_one_to_one_theme_constraint():
    assert ThemeProfile.__tablename__ == "theme_profiles"
    assert ThemeProfile.__table__.c.theme_id.unique is True


def test_driver_event_has_theme_url_unique_index():
    indexes = {index.name: index for index in ThemeDriverEvent.__table__.indexes}
    index = indexes["idx_theme_driver_events_theme_url"]
    assert index.unique is True
    assert [column.name for column in index.columns] == ["theme_id", "url_hash"]


def test_market_snapshot_distinguishes_zero_from_unavailable_limit_pool():
    assert ThemeMarketSnapshot.__table__.c.limit_up_count.nullable is True
    assert ThemeMarketSnapshot.__table__.c.limit_down_count.nullable is True
```

- [ ] **Step 2：运行测试并确认因模型不存在而失败**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_theme_insight_models.py -q`

Expected: FAIL，错误包含 `ModuleNotFoundError: No module named 'app.models.theme_profile'`。

- [ ] **Step 3：实现三个 ORM 模型及题材关系**

模型字段必须与设计文档一致。关键定义如下：

```python
class ThemeProfile(Base, TimestampMixin):
    __tablename__ = "theme_profiles"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    theme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("themes.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    core_logic: Mapped[str] = mapped_column(Text, nullable=False)
    applications: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    catalysts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    sources: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    theme: Mapped["Theme"] = relationship(back_populates="profile")
```

```python
class ThemeDriverEvent(Base, TimestampMixin):
    __tablename__ = "theme_driver_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    theme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    relevance_score: Mapped[int] = mapped_column(Integer, nullable=False)
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    theme: Mapped["Theme"] = relationship(back_populates="driver_events")
    __table_args__ = (
        Index("idx_theme_driver_events_theme_url", "theme_id", "url_hash", unique=True),
        Index("idx_theme_driver_events_theme_published", "theme_id", "published_at"),
    )
```

```python
class ThemeMarketSnapshot(Base, TimestampMixin):
    __tablename__ = "theme_market_snapshots"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    theme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("themes.id", ondelete="CASCADE"), nullable=False
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    up_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    down_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flat_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suspended_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    limit_up_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit_down_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    theme: Mapped["Theme"] = relationship(back_populates="market_snapshots")
    __table_args__ = (
        Index("idx_theme_market_snapshots_theme_date", "theme_id", "trade_date", unique=True),
    )
```

`Theme` 增加 `profile`、`driver_events`、`market_snapshots` 三个 `relationship`，并在 `models/__init__.py` 导入和导出新模型，保证 Alembic 可以发现元数据。

- [ ] **Step 4：编写迁移并验证升级/降级结构**

`010_create_theme_insights.py` 使用 `down_revision = "009_create_model_providers"`，按模型字段创建三张 InnoDB/utf8mb4 表和命名索引；`downgrade()` 按快照、事件、档案顺序删除表。

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_theme_insight_models.py -q`

Expected: PASS。

- [ ] **Step 5：提交模型和迁移**

```powershell
git add backend/alembic/versions/010_create_theme_insights.py backend/app/models/theme.py backend/app/models/theme_profile.py backend/app/models/theme_driver_event.py backend/app/models/theme_market_snapshot.py backend/app/models/__init__.py backend/tests/unit/test_theme_insight_models.py
git commit -m "feat(backend): add theme insight persistence"
```

## Task 2：定义 API 契约和仓储

**Files:**
- Create: `backend/app/schemas/theme_insight.py`
- Create: `backend/app/repositories/theme_insight.py`
- Create: `backend/app/domain/theme_insights.py`
- Modify: `backend/app/schemas/theme.py`
- Test: `backend/tests/unit/test_theme_schemas.py`
- Test: `backend/tests/unit/test_theme_insight_repository.py`

- [ ] **Step 1：写失败的 Schema 与仓储测试**

```python
def test_market_snapshot_ratio_is_null_when_down_count_is_zero():
    snapshot = ThemeMarketSnapshotResponse(
        trade_date=date(2026, 7, 20), up_count=12, down_count=0,
        flat_count=1, suspended_count=2, limit_up_count=3,
        limit_down_count=0, calculated_at=datetime.now(UTC),
    )
    assert snapshot.up_down_ratio is None
    assert snapshot.up_down_display == "12:0"


@pytest.mark.asyncio
async def test_recent_events_falls_back_to_30_days_when_seven_days_has_fewer_than_five(repo):
    items = await repo.list_recent_events(theme_id=1, now=NOW, limit=5)
    assert [item.title for item in items] == ["近一天", "近六天", "近十天"]
```

- [ ] **Step 2：运行定向测试确认契约和仓储尚不存在**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_theme_schemas.py tests/unit/test_theme_insight_repository.py -q`

Expected: FAIL，缺少 `ThemeMarketSnapshotResponse` 或 `ThemeInsightRepository`。

- [ ] **Step 3：实现 Pydantic 契约**

在 `theme_insight.py` 定义：

```python
class SourceReference(BaseModel):
    title: str
    url: str
    publisher: str | None = None
    published_at: datetime | None = None


class ThemeProfileResponse(BaseModel):
    definition: str
    core_logic: str
    applications: list[str]
    catalysts: list[str]
    risks: list[str]
    sources: list[SourceReference]
    generated_at: datetime
    model_config = {"from_attributes": True}


class ThemeMarketSnapshotResponse(BaseModel):
    trade_date: date
    up_count: int
    down_count: int
    flat_count: int
    suspended_count: int
    limit_up_count: int | None
    limit_down_count: int | None
    calculated_at: datetime

    @computed_field
    @property
    def up_down_ratio(self) -> float | None:
        return round(self.up_count / self.down_count, 2) if self.down_count else None

    @computed_field
    @property
    def up_down_display(self) -> str:
        return f"{self.up_count}:{self.down_count}"
```

同时定义 `ThemeDriverEventResponse`、`ExtractedThemeProfile`、`ExtractedDriverEvent`、`ExtractedThemeInsights`、`ThemeInsightRefreshResponse`。抽取模型限制相关性为 `0..100`，列表字段使用 `Field(default_factory=list)`。

在 `schemas/theme.py` 的 `ThemeDetailResponse` 增加：

```python
profile: ThemeProfileResponse | None = None
recent_driver_events: list[ThemeDriverEventResponse] = Field(default_factory=list)
market_snapshot: ThemeMarketSnapshotResponse | None = None
```

- [ ] **Step 4：实现仓储的读取和幂等写入**

先在 `domain/theme_insights.py` 定义 `MarketCounts` 不可变数据类，字段为 `up_count`、`down_count`、`flat_count`、`suspended_count`、`limit_up_count` 和 `limit_down_count`，后两个字段允许 `None`。仓储和后续行情服务统一使用该类型。

`ThemeInsightRepository` 提供以下明确接口：

`get_profile(theme_id)` 返回档案或 `None`；`upsert_profile(theme_id, payload, sources, generated_at)` 返回写入后的档案；`list_recent_events(theme_id, now, limit=5)` 返回事件列表；`upsert_events(theme_id, events)` 返回新增数和更新数；`get_latest_snapshot(theme_id)` 返回最新快照或 `None`；`upsert_snapshot(theme_id, trade_date, counts, calculated_at)` 返回当天快照。

`list_recent_events` 先查询 7 天；不足 5 条时重新查询 30 天，而不是把两个结果拼接造成重复。`upsert_events` 使用 MySQL `insert().on_duplicate_key_update(...)`，以题材和 URL 哈希保持幂等。

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_theme_schemas.py tests/unit/test_theme_insight_repository.py -q`

Expected: PASS。

- [ ] **Step 5：提交契约和仓储**

```powershell
git add backend/app/schemas/theme.py backend/app/schemas/theme_insight.py backend/app/domain/theme_insights.py backend/app/repositories/theme_insight.py backend/tests/unit/test_theme_schemas.py backend/tests/unit/test_theme_insight_repository.py
git commit -m "feat(backend): add theme insight contracts and repository"
```

## Task 3：实现行情分类和涨跌停池适配

**Files:**
- Modify: `backend/app/domain/theme_insights.py`
- Create: `backend/app/integrations/market/__init__.py`
- Create: `backend/app/integrations/market/limit_pool.py`
- Create: `backend/app/services/theme_market.py`
- Modify: `backend/app/repositories/theme.py`
- Test: `backend/tests/unit/test_theme_insight_domain.py`
- Test: `backend/tests/unit/test_limit_pool.py`
- Test: `backend/tests/unit/test_theme_market_service.py`

- [ ] **Step 1：写失败的行情纯函数和服务测试**

```python
def test_classify_market_counts_excludes_missing_quotes_from_ratio():
    stocks = [FakeStock("000001", Decimal("2.1")), FakeStock("000002", Decimal("-1")),
              FakeStock("000003", Decimal("0")), FakeStock("000004", None)]
    counts = classify_market_counts(stocks, {"000001"}, {"000002"})
    assert counts == MarketCounts(
        up_count=1, down_count=1, flat_count=1, suspended_count=1,
        limit_up_count=1, limit_down_count=1,
    )


@pytest.mark.asyncio
async def test_refresh_all_fetches_limit_pools_once(service, provider, repo):
    await service.refresh_all(date(2026, 7, 20))
    provider.fetch.assert_awaited_once_with(date(2026, 7, 20))
    assert repo.upsert_snapshot.await_count == 2
```

- [ ] **Step 2：运行测试并确认失败**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_theme_insight_domain.py tests/unit/test_limit_pool.py tests/unit/test_theme_market_service.py -q`

Expected: FAIL，缺少市场领域函数和适配器。

- [ ] **Step 3：实现纯函数与 AKShare 适配器**

`theme_insights.py` 定义不可变计数对象和分类函数：

```python
@dataclass(frozen=True, slots=True)
class MarketCounts:
    up_count: int
    down_count: int
    flat_count: int
    suspended_count: int
    limit_up_count: int | None
    limit_down_count: int | None


def normalize_stock_code(value: object) -> str:
    return str(value).strip().split(".")[-1].zfill(6)
```

`LimitPoolProvider.fetch(trade_date)` 通过 `asyncio.to_thread` 调用官方 AKShare 接口 `stock_zt_pool_em(date="YYYYMMDD")` 和 `stock_zt_pool_dtgc_em(date="YYYYMMDD")`，从 DataFrame 的“代码”列返回两个代码集合。两个池分别捕获异常；某一池失败时对应集合为 `None`，不能伪装为空集合。

- [ ] **Step 4：实现批量市场快照服务**

在 `ThemeRepository` 新增一次加载全部有效题材及其成分股行情的方法，使用 `selectinload` 避免 N+1。`ThemeMarketService.refresh_all()` 只抓取一次全市场涨跌停池，然后逐题材调用 `classify_market_counts` 和 `ThemeInsightRepository.upsert_snapshot`，最后一次提交事务。

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_theme_insight_domain.py tests/unit/test_limit_pool.py tests/unit/test_theme_market_service.py -q`

Expected: PASS。

- [ ] **Step 5：提交行情统计实现**

```powershell
git add backend/app/domain/theme_insights.py backend/app/integrations/market backend/app/services/theme_market.py backend/app/repositories/theme.py backend/tests/unit/test_theme_insight_domain.py backend/tests/unit/test_limit_pool.py backend/tests/unit/test_theme_market_service.py
git commit -m "feat(backend): aggregate theme market breadth"
```

## Task 4：扩展公开资料采集能力

**Files:**
- Modify: `backend/app/services/web_research.py`
- Modify: `backend/app/repositories/news.py`
- Test: `backend/tests/unit/test_web_research.py`
- Test: `backend/tests/unit/test_news_repository.py`

- [ ] **Step 1：写失败的搜索、反爬注入和新闻候选测试**

```python
@pytest.mark.asyncio
async def test_research_driver_events_uses_theme_and_stock_queries(service):
    service.search = AsyncMock(return_value=[])
    await service.research_driver_events("机器人", ["拓斯达", "埃斯顿"])
    queries = [call.args[0] for call in service.search.await_args_list]
    assert any("机器人" in query and "政策" in query for query in queries)
    assert any("拓斯达" in query for query in queries)


@pytest.mark.asyncio
async def test_news_candidates_filter_by_theme_or_stock_keyword(repo):
    items = await repo.list_theme_candidates(["机器人", "埃斯顿"], since=NOW - timedelta(days=30))
    assert [item.title for item in items] == ["机器人产业政策发布"]
```

- [ ] **Step 2：运行测试并确认缺少新接口**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_web_research.py tests/unit/test_news_repository.py -q`

Expected: FAIL，缺少 `research_profile`、`research_driver_events` 或 `list_theme_candidates`。

- [ ] **Step 3：让网页研究服务复用反爬能力**

`WebResearchService` 构造函数接受可注入的 `AntiScrapingMiddleware`，搜索和正文请求统一经中间件发送，同时保留 `validate_public_url` 和重定向后再次校验。新增两个聚焦入口：

`research_profile(theme_name)` 返回档案资料来源列表；`research_driver_events(theme_name, stock_names)` 返回驱动事件候选来源列表。

档案查询覆盖概念、产业链、应用、催化和风险；事件查询覆盖题材名、最多 10 个核心成分股名及政策、订单、发布、突破、涨价、扩产和业绩语义。所有 URL 统一去重，每批最多抓取配置的来源数。

- [ ] **Step 4：增加近 30 天新闻候选查询**

`NewsRepository.list_theme_candidates(keywords, since, limit=50)` 使用转义后的 `LIKE` 条件匹配标题和摘要，要求 `published_at >= since`，按发布时间倒序返回。空关键词直接返回空列表，避免生成无条件全表查询。

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_web_research.py tests/unit/test_news_repository.py -q`

Expected: PASS。

- [ ] **Step 5：提交采集扩展**

```powershell
git add backend/app/services/web_research.py backend/app/repositories/news.py backend/tests/unit/test_web_research.py backend/tests/unit/test_news_repository.py
git commit -m "feat(backend): collect theme research sources"
```

## Task 5：实现 AI 抽取、关键词降级和增量刷新

**Files:**
- Modify: `backend/app/domain/theme_insights.py`
- Create: `backend/app/services/theme_insight.py`
- Test: `backend/tests/unit/test_theme_insight_service.py`

- [ ] **Step 1：写失败的刷新服务测试**

```python
@pytest.mark.asyncio
async def test_refresh_persists_valid_profile_and_relevant_events(service, repo):
    result = await service.refresh(theme_id=1)
    repo.upsert_profile.assert_awaited_once()
    repo.upsert_events.assert_awaited_once()
    assert result.profile_updated is True
    assert result.inserted_events == 2
    assert result.degraded is False


@pytest.mark.asyncio
async def test_ai_failure_keeps_profile_and_uses_keyword_event_fallback(service, repo):
    service.providers.get_default.side_effect = HTTPException(409, "未配置模型")
    result = await service.refresh(theme_id=1)
    repo.upsert_profile.assert_not_awaited()
    repo.upsert_events.assert_awaited_once()
    assert result.profile_updated is False
    assert result.degraded is True


@pytest.mark.asyncio
async def test_all_sources_failed_preserves_existing_data(service, repo):
    service.research.research_profile.return_value = []
    service.research.research_driver_events.return_value = []
    service.news.list_theme_candidates.return_value = []
    with pytest.raises(HTTPException) as error:
        await service.refresh(theme_id=1)
    assert error.value.status_code == 502
    repo.delete_existing.assert_not_called()
```

- [ ] **Step 2：运行测试并确认刷新服务不存在**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_theme_insight_service.py -q`

Expected: FAIL，缺少 `ThemeInsightRefreshService`。

- [ ] **Step 3：实现可校验的模型抽取**

`ThemeInsightRefreshService` 复用 `ModelProviderService` 和 `parse_model_json`。系统提示明确要求只基于提供来源返回 JSON：

```json
{
  "profile": {
    "definition": "工业机器人是面向工业场景执行自动化任务的机器系统",
    "core_logic": "制造业自动化投入提升带动本体、控制器和减速器需求",
    "applications": ["汽车制造", "电子装配"],
    "catalysts": ["产业支持政策发布", "核心零部件国产化"],
    "risks": ["制造业资本开支下降", "行业价格竞争加剧"],
    "source_urls": ["https://example.com/source"]
  },
  "events": [{
    "title": "机器人产业支持政策发布",
    "summary": "政策提出扩大工业机器人示范应用范围",
    "source_url": "https://example.com/event",
    "published_at": "2026-07-20T08:00:00+08:00",
    "relevance_score": 88
  }]
}
```

解析后使用 `ExtractedThemeInsights.model_validate()`；所有 `source_url` 必须属于实际抓取或新闻候选 URL，事件相关性低于 60 不入库，摘要限制长度，模型异常不得覆盖旧档案。

- [ ] **Step 4：实现关键词降级和事务编排**

领域函数 `keyword_event_fallback(theme_name, stock_names, candidates)` 只有在标题或摘要同时命中题材/成分股词与至少一个驱动词时才返回事件；相关性固定为 40，并保留原始标题、来源、URL 和发布时间。

`refresh(theme_id)` 的流程固定为：加载题材与最多 10 个成分股、并行采集档案网页/事件网页/近 30 天新闻、尝试 AI 抽取、在 AI 失败时仅对事件降级、以单个事务写入新档案和事件、返回 `ThemeInsightRefreshResponse`。若所有来源为空则返回 502；部分来源失败写入 `failed_sources`，不阻断有效结果。

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_theme_insight_service.py -q`

Expected: PASS。

- [ ] **Step 5：提交研究刷新服务**

```powershell
git add backend/app/domain/theme_insights.py backend/app/services/theme_insight.py backend/tests/unit/test_theme_insight_service.py
git commit -m "feat(backend): refresh theme profiles and driver events"
```

## Task 6：接入详情 API 和手动刷新端点

**Files:**
- Modify: `backend/app/services/theme.py`
- Modify: `backend/app/api/theme.py`
- Modify: `backend/tests/unit/test_theme_service.py`
- Modify: `backend/tests/integration/test_theme_api.py`

- [ ] **Step 1：写失败的详情聚合和刷新接口测试**

```python
@pytest.mark.asyncio
async def test_get_theme_detail_includes_insights(theme_service):
    result = await theme_service.get_theme_detail(1)
    assert result.profile.definition == "机器人是自动执行任务的机器系统"
    assert len(result.recent_driver_events) == 1
    assert result.market_snapshot.up_down_display == "12:8"


def test_refresh_theme_insights_endpoint(client):
    response = client.post("/api/v1/themes/1/insights/refresh")
    assert response.status_code == 200
    assert response.json()["message"] == "题材资料已更新"
```

- [ ] **Step 2：运行测试并确认详情字段或路由缺失**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_theme_service.py tests/integration/test_theme_api.py -q`

Expected: FAIL，详情响应缺少新字段，刷新端点返回 404。

- [ ] **Step 3：聚合题材洞察数据**

`ThemeService.__init__` 接受可注入的 `ThemeInsightRepository`，`get_theme_detail()` 在加载现有产业链和概念图谱后读取：

```python
profile = await self.insights.get_profile(theme_id)
events = await self.insights.list_recent_events(theme_id, now=datetime.now(UTC), limit=5)
snapshot = await self.insights.get_latest_snapshot(theme_id)
```

将三个值分别转换为 `ThemeProfileResponse`、`ThemeDriverEventResponse` 和 `ThemeMarketSnapshotResponse`；无数据分别返回 `None`、`[]`、`None`。

- [ ] **Step 4：新增手动刷新端点**

在动态 `/{theme_id}` 详情路由之前声明：

```python
@router.post(
    "/{theme_id}/insights/refresh",
    response_model=ThemeInsightRefreshResponse,
)
async def refresh_theme_insights(
    theme_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await ThemeInsightRefreshService(db).refresh(theme_id)
```

保留 `HTTPException` 的中文 detail，未处理异常继续交给全局异常处理器。

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_theme_service.py tests/integration/test_theme_api.py -q`

Expected: PASS。

- [ ] **Step 5：提交 API 接入**

```powershell
git add backend/app/services/theme.py backend/app/api/theme.py backend/tests/unit/test_theme_service.py backend/tests/integration/test_theme_api.py
git commit -m "feat(api): expose theme insights in detail"
```

## Task 7：接入定时任务和行情刷新链路

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Create: `backend/app/services/theme_insight_scheduler.py`
- Modify: `backend/app/scrapers/eastmoney.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/unit/test_theme_insight_scheduler.py`
- Modify: `backend/tests/unit/test_scraper_akshare.py`
- Modify: `backend/tests/unit/test_app_lifespan.py`

- [ ] **Step 1：写失败的周期任务和行情触发测试**

```python
@pytest.mark.asyncio
async def test_lifespan_starts_and_stops_theme_insight_periodic(monkeypatch):
    settings.THEME_INSIGHT_AUTO_ENABLED = True
    async with app.router.lifespan_context(app):
        insight_scheduler.start.assert_called_once_with(interval_seconds=3600)
    insight_scheduler.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_eastmoney_run_refreshes_market_snapshots_after_stock_save(scraper):
    await scraper.run("", {})
    scraper.market_service.refresh_all.assert_awaited_once()
```

- [ ] **Step 2：运行测试并确认配置和调度器缺失**

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_theme_insight_scheduler.py tests/unit/test_scraper_akshare.py tests/unit/test_app_lifespan.py -q`

Expected: FAIL，缺少研究调度器或配置项。

- [ ] **Step 3：实现有界的题材研究周期任务**

新增配置：

```python
THEME_INSIGHT_AUTO_ENABLED: bool = True
THEME_INSIGHT_INTERVAL_SECONDS: int = 3600
THEME_PROFILE_MAX_AGE_DAYS: int = 7
THEME_INSIGHT_BATCH_SIZE: int = 10
```

实现 `ThemeInsightScheduler`：每轮选择最多 10 个“档案缺失/过期或事件最后抓取时间最旧”的有效题材，逐个调用 `ThemeInsightRefreshService.refresh()`；每个题材单独事务和异常边界，避免一个题材失败中止整批。`start()` 防止重复启动，`stop()` 取消并等待任务退出。

- [ ] **Step 4：连接应用生命周期和市场快照刷新**

`main.py` 在启用配置时启动和停止研究周期任务。`EastMoneyScraper` 完成全部题材及成分股持久化后，在新的数据库会话中调用一次 `ThemeMarketService.refresh_all()`；若涨跌停池失败，记录警告并按可空字段规则保存可用的涨跌统计，不能把整个行情采集标记为失败。

Run: `cd backend; .\.venv\Scripts\python.exe -m pytest tests/unit/test_theme_insight_scheduler.py tests/unit/test_scraper_akshare.py tests/unit/test_app_lifespan.py -q`

Expected: PASS。

- [ ] **Step 5：提交调度集成**

```powershell
git add backend/app/core/config.py backend/.env.example backend/app/services/theme_insight_scheduler.py backend/app/scrapers/eastmoney.py backend/app/main.py backend/tests/unit/test_theme_insight_scheduler.py backend/tests/unit/test_scraper_akshare.py backend/tests/unit/test_app_lifespan.py
git commit -m "feat(backend): schedule theme insight refreshes"
```

## Task 8：同步前端类型和 API

**Files:**
- Modify: `frontend/src/types/theme.ts`
- Modify: `frontend/src/api/theme.ts`
- Modify: `frontend/src/api/theme.test.ts`

- [ ] **Step 1：写失败的前端刷新 API 测试**

```typescript
it('refreshes theme insights', async () => {
  vi.mocked(apiClient.post).mockResolvedValue({ data: refreshResponse })
  await refreshThemeInsights(12)
  expect(apiClient.post).toHaveBeenCalledWith('/themes/12/insights/refresh')
})
```

- [ ] **Step 2：运行测试并确认函数不存在**

Run: `cd frontend; pnpm vitest run src/api/theme.test.ts`

Expected: FAIL，错误包含 `refreshThemeInsights is not a function` 或缺少导出。

- [ ] **Step 3：添加完整 TypeScript 契约**

在 `types/theme.ts` 增加 `ThemeSourceReference`、`ThemeProfile`、`ThemeDriverEvent`、`ThemeMarketSnapshot` 和 `ThemeInsightRefreshResponse`，并扩展详情类型：

```typescript
export interface ThemeDetailResponse {
  id: number
  name: string
  code: string
  description: string | null
  heat_index: number
  rise_fall_pct: number
  stock_count: number
  category: string | null
  tags: string[] | Record<string, unknown> | null
  source: string | null
  created_at: string
  updated_at: string
  industry_chains: {
    upstream: IndustryChainBrief[]
    midstream: IndustryChainBrief[]
    downstream: IndustryChainBrief[]
  }
  chain_stock_counts: {
    upstream: number
    midstream: number
    downstream: number
  }
  concept_graph: ConceptGraph
  profile: ThemeProfile | null
  recent_driver_events: ThemeDriverEvent[]
  market_snapshot: ThemeMarketSnapshot | null
}
```

数值字段使用 `number`，日期使用 ISO 字符串，`limit_up_count`、`limit_down_count` 和 `up_down_ratio` 使用 `number | null`。

- [ ] **Step 4：实现刷新 API 函数并通过测试**

```typescript
export async function refreshThemeInsights(
  themeId: number
): Promise<ThemeInsightRefreshResponse> {
  const { data } = await apiClient.post<ThemeInsightRefreshResponse>(
    `/themes/${themeId}/insights/refresh`
  )
  return data
}
```

Run: `cd frontend; pnpm vitest run src/api/theme.test.ts`

Expected: PASS。

- [ ] **Step 5：提交前端契约**

```powershell
git add frontend/src/types/theme.ts frontend/src/api/theme.ts frontend/src/api/theme.test.ts
git commit -m "feat(frontend): add theme insight API contracts"
```

## Task 9：实现三个详情展示组件

**Files:**
- Create: `frontend/src/components/ThemeMarketBreadth.tsx`
- Create: `frontend/src/components/ThemeMarketBreadth.test.tsx`
- Create: `frontend/src/components/ThemeProfileSection.tsx`
- Create: `frontend/src/components/ThemeProfileSection.test.tsx`
- Create: `frontend/src/components/ThemeDriverEvents.tsx`
- Create: `frontend/src/components/ThemeDriverEvents.test.tsx`

- [ ] **Step 1：写三个组件的失败测试**

```typescript
it('distinguishes unavailable limit count from zero', () => {
  render(<ThemeMarketBreadth snapshot={{ ...snapshot, limit_up_count: null, limit_down_count: 0 }} />)
  expect(screen.getByTestId('limit-up-count')).toHaveTextContent('暂无数据')
  expect(screen.getByTestId('limit-down-count')).toHaveTextContent('0')
  expect(screen.getByText('12:0')).toBeInTheDocument()
})

it('renders structured profile and source links', () => {
  render(<ThemeProfileSection profile={profile} />)
  expect(screen.getByText('核心逻辑')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: '来源一' })).toHaveAttribute('href', profile.sources[0].url)
})

it('renders at most five driver events', () => {
  render(<ThemeDriverEvents events={sixEvents} />)
  expect(screen.getAllByTestId('driver-event')).toHaveLength(5)
})
```

- [ ] **Step 2：运行测试并确认组件缺失**

Run: `cd frontend; pnpm vitest run src/components/ThemeMarketBreadth.test.tsx src/components/ThemeProfileSection.test.tsx src/components/ThemeDriverEvents.test.tsx`

Expected: FAIL，三个组件模块不存在。

- [ ] **Step 3：实现行情和档案组件**

`ThemeMarketBreadth` 使用语义化 `<section>` 和紧凑响应式网格，分别渲染涨停、跌停、上涨、下跌、上涨:下跌和交易日期。只对 `null` 显示“暂无数据”，真实 `0` 必须显示 `0`。

`ThemeProfileSection` 分段渲染定义、核心逻辑、应用、催化和风险；来源使用：

```tsx
<a href={source.url} target="_blank" rel="noopener noreferrer">
  {source.title}
</a>
```

`profile === null` 时显示“暂无详细介绍，可点击刷新题材资料获取”。

- [ ] **Step 4：实现事件时间线组件并通过测试**

`ThemeDriverEvents` 对 `events.slice(0, 5)` 渲染时间线，包含 `published_at`、标题、摘要、来源、相关性分数和安全原文链接；空数组显示“近 30 天暂未发现可靠驱动事件”。长标题和 URL 容器使用可换行样式，避免移动端溢出。

Run: `cd frontend; pnpm vitest run src/components/ThemeMarketBreadth.test.tsx src/components/ThemeProfileSection.test.tsx src/components/ThemeDriverEvents.test.tsx`

Expected: PASS。

- [ ] **Step 5：提交详情组件**

```powershell
git add frontend/src/components/ThemeMarketBreadth.tsx frontend/src/components/ThemeMarketBreadth.test.tsx frontend/src/components/ThemeProfileSection.tsx frontend/src/components/ThemeProfileSection.test.tsx frontend/src/components/ThemeDriverEvents.tsx frontend/src/components/ThemeDriverEvents.test.tsx
git commit -m "feat(frontend): render theme research insights"
```

## Task 10：组合详情页、完成回归验证

**Files:**
- Modify: `frontend/src/features/themes/ThemeDetail.tsx`
- Modify: `frontend/src/features/themes/ThemeDetail.test.tsx`
- Verify: `backend/tests/`
- Verify: `frontend/src/`

- [ ] **Step 1：写失败的详情页组合和刷新测试**

```typescript
it('renders market breadth, profile and driver events before existing charts', async () => {
  vi.mocked(fetchThemeDetail).mockResolvedValue(mockThemeDetailWithInsights)
  renderThemeDetail()
  const profile = await screen.findByRole('heading', { name: '题材详细介绍' })
  const events = screen.getByRole('heading', { name: '最近驱动事件' })
  const chart = screen.getByTestId('heat-trend-line')
  expect(profile.compareDocumentPosition(events) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(events.compareDocumentPosition(chart) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
})

it('refreshes insights and then refetches detail', async () => {
  const user = userEvent.setup()
  vi.mocked(refreshThemeInsights).mockResolvedValue(refreshResponse)
  renderThemeDetail()
  await user.click(await screen.findByRole('button', { name: '刷新题材资料' }))
  expect(refreshThemeInsights).toHaveBeenCalledWith(1)
  await waitFor(() => expect(fetchThemeDetail).toHaveBeenCalledTimes(2))
})
```

- [ ] **Step 2：运行详情页测试并确认新区域尚未组合**

Run: `cd frontend; pnpm vitest run src/features/themes/ThemeDetail.test.tsx`

Expected: FAIL，找不到“题材详细介绍”“最近驱动事件”或刷新按钮。

- [ ] **Step 3：组合组件和独立刷新状态**

在 `ThemeDetail.tsx`：

- 导入三个组件和 `refreshThemeInsights`；
- 新增独立 `insightRefresh` mutation；
- 成功后调用详情查询的 `refetch()`；
- 页头同时显示“刷新题材资料”和“刷新图谱”，两者禁用状态互不混用；
- 将 `ThemeMarketBreadth` 放在顶部摘要后，将 `ThemeProfileSection` 和 `ThemeDriverEvents` 放在原有图表前；
- 刷新部分成功时显示返回的中文消息和失败来源；失败时保留已加载数据并显示统一中文错误。

Run: `cd frontend; pnpm vitest run src/features/themes/ThemeDetail.test.tsx`

Expected: PASS。

- [ ] **Step 4：执行格式、完整测试和迁移验证**

Run:

```powershell
cd backend
.\.venv\Scripts\python.exe -m ruff check app tests
.\.venv\Scripts\python.exe -m black --check app tests
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing
cd ..\frontend
pnpm lint
pnpm vitest run
pnpm build
```

Expected: Ruff、Black、pytest、ESLint、Vitest 和 Vite build 全部退出码为 0。测试环境数据库运行 `alembic upgrade head` 后当前 revision 为 `010_create_theme_insights`；再执行一次升级不产生额外变更。

- [ ] **Step 5：执行真实服务冒烟验证**

启动现有 MySQL、后端和前端后验证：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/themes/1
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/themes/1/insights/refresh
```

Expected: 详情响应包含 `profile`、`recent_driver_events` 和 `market_snapshot`；刷新响应包含档案更新状态、事件计数、失败来源和中文消息。打开 `http://localhost:5173/themes/1` 可见新增区域，原有图谱、成分股和产业链仍可使用。

- [ ] **Step 6：提交组合与验证结果**

```powershell
git add frontend/src/features/themes/ThemeDetail.tsx frontend/src/features/themes/ThemeDetail.test.tsx
git commit -m "feat(frontend): integrate theme insights into detail page"
```

## 最终验收清单

- [ ] 三张新表的迁移、唯一约束、可空涨跌停字段和级联关系正确。
- [ ] 详情 API 对完整、部分缺失和完全缺失洞察数据均保持兼容。
- [ ] 研究刷新按 URL 幂等增量写入，AI 失败时只降级事件，不覆盖已有档案。
- [ ] 事件严格最多 5 条，先查 7 天，不足时扩展到 30 天。
- [ ] 涨跌分类排除平盘和停牌；真实零和数据不可用可区分。
- [ ] AKShare 涨停池、跌停池分别失败时不会伪造零值。
- [ ] 自动刷新有批量上限，不会重复启动，应用退出时可正常停止。
- [ ] 前端在桌面和移动宽度下无横向溢出，外链使用安全属性。
- [ ] 后端和前端完整测试、静态检查与构建通过。
