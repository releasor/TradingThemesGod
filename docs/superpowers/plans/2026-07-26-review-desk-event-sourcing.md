# 复盘台（事件溯源）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地独立路由 `/review` 的复盘台：run+事件溯源回放策略卡/候选/阶段迁移/涨跌验证，并支持 AI 题材日报 ensure（后台生成 + 规则降级）；经 Nav Card「复盘研究」切换进入，不改看板首页。

**Architecture:** 新表 `review_runs` / `review_events` / `review_ai_reports`；`ReviewEventWriter` 挂在 short-term refresh/analyze 路径写事件；`ReviewService` 按日/题材投影（无事件则读 `sector_rotation_snapshots` / `short_term_candidates` 等降级）；日报经 `asyncio.create_task` + 独立 `AsyncSessionLocal` 生成，避免堵 API worker。前端 `features/review` + Card Nav 新分组。

**Tech Stack:** FastAPI、SQLAlchemy Async、Alembic、MySQL 8、pytest、React、TanStack Query、Vitest、Tailwind。

**Spec:** `docs/superpowers/specs/2026-07-26-review-desk-event-sourcing-design.md`

**Commits:** 仅在用户明确要求时提交；步骤中的 commit 为建议信息，默认不自动执行。

---

## 文件结构

### 新建

| 文件 | 职责 |
|------|------|
| `backend/alembic/versions/016_create_review_desk_tables.py` | 三表 + 索引 |
| `backend/app/models/review.py` | `ReviewRun` / `ReviewEvent` / `ReviewAiReport` |
| `backend/app/schemas/review.py` | 日列表、日复盘、题材轴、日报 DTO |
| `backend/app/repositories/review.py` | run/event/report CRUD |
| `backend/app/services/review_events.py` | `ReviewEventWriter`：开跑/收跑/写事件 |
| `backend/app/services/review.py` | 日聚合、题材轴、涨跌验证、无事件降级 |
| `backend/app/services/review_report.py` | 规则摘要 + LLM 日报 + ensure |
| `backend/app/services/review_report_scheduler.py` | 可选盘后规则摘要任务（可先 stub） |
| `backend/app/api/review.py` | `/api/v1/review/*` |
| `backend/tests/unit/test_review_models.py` | ORM/索引 |
| `backend/tests/unit/test_review_events.py` | Writer |
| `backend/tests/unit/test_review_service.py` | 聚合与降级 |
| `backend/tests/unit/test_review_report_service.py` | ensure / fallback |
| `backend/tests/unit/test_review_api.py` | API mock |
| `frontend/src/types/review.ts` | 类型 |
| `frontend/src/api/review.ts` | API client |
| `frontend/src/api/review.test.ts` | client 测 |
| `frontend/src/features/review/ReviewDesk.tsx` | 双模式页 |
| `frontend/src/features/review/ReviewDesk.test.tsx` | UI 测 |
| `frontend/src/features/review/ReviewDayPanel.tsx` | 交易日轴区块 |
| `frontend/src/features/review/ReviewThemePanel.tsx` | 题材轴区块 |
| `frontend/src/features/review/ReviewReportPanel.tsx` | 日报区 |

### 修改

| 文件 | 变更 |
|------|------|
| `backend/app/models/__init__.py` | 注册三模型 |
| `backend/app/main.py` | `include_router(review_router)`；可选启动 report scheduler |
| `backend/app/services/short_term.py` | refresh/analyze 挂钩 `ReviewEventWriter` |
| `backend/app/services/sector_rotation.py` | rebuild 后写 `sector_stage_change`（经 writer 或回调） |
| `frontend/src/components/CardNav.tsx` | `CardNavTone` 增加 `review` + 色板 |
| `frontend/src/components/AppCardNav.tsx` | 「复盘研究」分组 |
| `frontend/src/components/AppCardNav.test.tsx` | 断言新入口 |
| `frontend/src/App.tsx` | lazy route `/review` |

### 已有可复用

- `ShortTermService.resolve_trade_date`、`get_overview` / `refresh_signals` / `analyze_from_database`
- `SectorRotationSnapshot.lifecycle_stage` / `strength_score`
- `ShortTermCandidate` 字段
- `StockAiReportService`（用户模型 + JSON complete 模式）
- `theme_insight_scheduler.py` / `ScraperScheduler`（`asyncio.create_task` + 独立 session）
- `MarketStrategyCard` 只读展示可抽 props 复用或简化复制只读块

---

### Task 1: 迁移 + ORM 三表

**Files:** `016_create_review_desk_tables.py`、`backend/app/models/review.py`、`models/__init__.py`、`test_review_models.py`

- [ ] **Step 1: 写失败的模型测试**

```python
from app.models.review import ReviewRun, ReviewEvent, ReviewAiReport

def test_review_run_columns_and_indexes():
    cols = {c.name for c in ReviewRun.__table__.columns}
    assert {"trade_date", "run_type", "status", "source_status", "request_meta", "started_at", "finished_at"} <= cols
    names = {i.name for i in ReviewRun.__table__.indexes}
    assert "idx_review_runs_date_started" in names

def test_review_event_columns_and_indexes():
    cols = {c.name for c in ReviewEvent.__table__.columns}
    assert {"run_id", "trade_date", "event_type", "entity_type", "entity_id", "payload_json", "occurred_at"} <= cols
    names = {i.name for i in ReviewEvent.__table__.indexes}
    assert "idx_review_events_date_type" in names
    assert "idx_review_events_entity" in names

def test_review_ai_report_unique():
    names = {c.name for c in ReviewAiReport.__table__.constraints if hasattr(c, "name") and c.name}
    # UniqueConstraint name
    assert "uq_review_ai_reports_date_user" in {
        u.name for u in ReviewAiReport.__table__.constraints if u.name
    }
```

- [ ] **Step 2: 运行确认失败**

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests/unit/test_review_models.py -q
```

Expected: import 失败。

- [ ] **Step 3: 实现 ORM**（`backend/app/models/review.py`）

```python
class ReviewRun(Base, TimestampMixin):
    __tablename__ = "review_runs"
    __table_args__ = (
        Index("idx_review_runs_date_started", "trade_date", "started_at"),
        Index("idx_review_runs_type_date", "run_type", "trade_date"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    run_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)  # running|success|partial|failed
    source_status: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    request_meta: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ReviewEvent(Base, TimestampMixin):
    __tablename__ = "review_events"
    __table_args__ = (
        Index("idx_review_events_date_type", "trade_date", "event_type"),
        Index("idx_review_events_run", "run_id"),
        Index("idx_review_events_entity", "entity_type", "entity_id", "trade_date"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("review_runs.id", ondelete="CASCADE"), nullable=True
    )
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class ReviewAiReport(Base, TimestampMixin):
    __tablename__ = "review_ai_reports"
    __table_args__ = (
        UniqueConstraint("trade_date", "user_id", name="uq_review_ai_reports_date_user"),
        Index("ix_review_ai_reports_trade_date", "trade_date"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    content_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    model_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_run_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
```

**MySQL 注意：** `UNIQUE(trade_date, user_id)` 下多行 `user_id=NULL` 在 MySQL 允许；全局规则摘要用 `user_id IS NULL` 时在仓库层 `get_rule_report(trade_date)` 取最新一条，或固定用 `user_id=0` 哨兵——**采用 `user_id` 可空 + 仓库 `get_latest_null_user(trade_date)`，ensure 时先查再插，避免依赖 partial unique。**

- [ ] **Step 4: Alembic `016`**

`revision = "016_create_review_desk_tables"`  
`down_revision = "015_create_short_term_radar_tables"`  

三表 `mysql_engine="InnoDB"`、`mysql_charset="utf8mb4"`、`mysql_collate="utf8mb4_0900_ai_ci"`（与早期迁移一致，满足 `test_mysql_migrations` 若扩展到 016；至少不要用 Postgres DDL）。

- [ ] **Step 5: 注册 `models/__init__.py`，重跑测试至 PASS**

```bash
.\.venv\Scripts\python.exe -m pytest tests/unit/test_review_models.py -q
.\.venv\Scripts\alembic.exe upgrade head
```

---

### Task 2: Repository

**Files:** `backend/app/repositories/review.py`、可在 `test_review_events.py` 用 mock session 测

- [ ] **Step 1: 实现方法**

```python
class ReviewRepository:
    async def create_run(self, *, trade_date, run_type, request_meta=None) -> ReviewRun: ...
    async def finish_run(self, run_id, *, status, source_status=None, error=None) -> None: ...
    async def add_event(self, *, run_id, trade_date, event_type, entity_type, entity_id, payload, occurred_at=None) -> ReviewEvent: ...
    async def list_runs(self, trade_date: date) -> list[ReviewRun]: ...
    async def list_events(self, trade_date: date, event_types: list[str] | None = None) -> list[ReviewEvent]: ...
    async def list_theme_events(self, theme_id: int, start: date, end: date) -> list[ReviewEvent]: ...
    async def list_trade_dates(self, start: date, end: date) -> list[date]: ...
    async def get_report(self, trade_date: date, user_id: int | None) -> ReviewAiReport | None: ...
    async def upsert_report(...) -> ReviewAiReport: ...
```

`create_run`：`status="running"`，`started_at=utcnow`。  
`finish_run`：写 `finished_at`、`status`、合并 `source_status`。

- [ ] **Step 2: 最小单测（AsyncMock session）** — create_run 调用 `session.add`；finish_run 更新字段。

---

### Task 3: ReviewEventWriter（TDD）

**Files:** `backend/app/services/review_events.py`、`tests/unit/test_review_events.py`

- [ ] **Step 1: 失败测试**

```python
@pytest.mark.asyncio
async def test_writer_records_strategy_card_event():
    repo = AsyncMock()
    run = SimpleNamespace(id=1, trade_date=date(2026, 7, 24))
    repo.create_run.return_value = run
    writer = ReviewEventWriter(repo)
    async with writer.track(trade_date=date(2026, 7, 24), run_type="overview_analyze") as ctx:
        await ctx.emit_strategy_card({"title": "指数情绪策略卡", "primary_strategy": "连板接力"})
    repo.add_event.assert_awaited()
    kwargs = repo.add_event.await_args.kwargs
    assert kwargs["event_type"] == "strategy_card"
    repo.finish_run.assert_awaited_with(1, status="success", source_status=ANY, error=None)
```

```python
@pytest.mark.asyncio
async def test_writer_marks_failed_on_exception():
    repo = AsyncMock()
    repo.create_run.return_value = SimpleNamespace(id=9, trade_date=date(2026, 7, 24))
    writer = ReviewEventWriter(repo)
    with pytest.raises(RuntimeError):
        async with writer.track(trade_date=date(2026, 7, 24), run_type="signals_refresh") as ctx:
            raise RuntimeError("boom")
    repo.finish_run.assert_awaited()
    assert repo.finish_run.await_args.kwargs["status"] == "failed"
```

- [ ] **Step 2: 实现 `ReviewEventWriter`**

```python
class ReviewRunContext:
    def __init__(self, repo, run): ...
    async def emit(self, event_type, entity_type, payload, entity_id=None): ...
    async def emit_strategy_card(self, payload: dict): ...
    async def emit_candidate(self, stock_id, payload: dict): ...
    async def emit_stage_change(self, theme_id, payload: dict): ...
    async def emit_emotion(self, payload: dict): ...
    async def emit_signal_batch(self, payload: dict): ...
    async def emit_quote_refresh(self, payload: dict): ...
    def set_partial(self, source_status: dict): ...

class ReviewEventWriter:
    def __init__(self, repo: ReviewRepository): ...
    @asynccontextmanager
    async def track(self, *, trade_date, run_type, request_meta=None):
        run = await self.repo.create_run(...)
        ctx = ReviewRunContext(...)
        try:
            yield ctx
            status = "partial" if ctx._partial else "success"
            await self.repo.finish_run(run.id, status=status, source_status=ctx.source_status)
        except Exception as exc:
            await self.repo.finish_run(run.id, status="failed", source_status=ctx.source_status, error=str(exc))
            raise
```

- [ ] **Step 3: 测试 PASS**

---

### Task 4: 挂钩 short-term / sector_rotation

**Files:** `backend/app/services/short_term.py`、`backend/app/services/sector_rotation.py`、扩展 `test_short_term_service.py`（mock writer）

- [ ] **Step 1: 在 `ShortTermService` 注入/懒创建 Writer**

```python
def _review_writer(self) -> ReviewEventWriter:
    return ReviewEventWriter(ReviewRepository(self.session))
```

- [ ] **Step 2: `refresh_signals`**

在方法主体外包 `async with writer.track(trade_date=..., run_type="signals_refresh") as ctx:`  
结束前 `await ctx.emit_signal_batch({"counts": ...})`；若已有 short_term_signal_runs，仍保留原表，review_runs 并行写入。  
候选落库后循环 Top N（如 50）`emit_candidate`。  
`SectorRotationService.rebuild` 返回或内部对比前日 `lifecycle_stage`，变化则 `emit_stage_change`（payload: `from_stage`, `to_stage`, `strength_score`）。

- [ ] **Step 3: `analyze_from_database` / `_build_overview` 路径**

`run_type="overview_analyze"`：写出 `strategy_card`（title、index/emotion strength、primary/secondary、rationale 摘要）、`emotion_snapshot`。

- [ ] **Step 4: `refresh_data_and_get_overview`**

`run_type="quote_refresh"`：一条摘要 `quote_refresh`（codes 数量、source），再链 overview 事件或同 run 内写 strategy_card。

原则：挂钩失败 **不得** 让主流程 500——`try/except` 记日志后吞掉 Writer 错误（或仅 finish failed）；主业务异常仍要 finish review run。

- [ ] **Step 5: 单测** — mock writer，断言 `refresh_signals` 调用 `track`；Writer 抛错时 overview 仍返回。

---

### Task 5: ReviewService 聚合 + 降级（TDD）

**Files:** `backend/app/services/review.py`、`backend/app/schemas/review.py`、`tests/unit/test_review_service.py`

- [ ] **Step 1: Schema 要点**

```python
class ReviewDayResponse(BaseModel):
    trade_date: date
    degraded: bool
    missing_sources: list[str]
    runs: list[ReviewRunBrief]
    strategy_card: dict | None
    candidates: list[ReviewCandidateItem]
    stage_transitions: list[ReviewStageTransition]
    performance: ReviewPerformance | None
    report_summary: str | None = None

class ReviewThemeResponse(BaseModel):
    theme_id: int
    theme_name: str
    days: int
    trajectory: list[ReviewThemeDayPoint]  # date, stage, strength_score, rise_fall_pct?
    related_candidates: list[ReviewCandidateItem]
    run_refs: list[ReviewRunBrief]
```

- [ ] **Step 2: 测试**

```python
@pytest.mark.asyncio
async def test_day_review_uses_events_when_present():
    # repo.list_events 返回 strategy_card + candidates → degraded False

@pytest.mark.asyncio
async def test_day_review_degrades_to_snapshots_without_events():
    # list_events=[]；从 SectorRotationSnapshot / ShortTermCandidate 查询（mock execute）
    # → degraded True, missing_sources 含 "review_events"
```

- [ ] **Step 3: 实现 `ReviewService`**

```python
class ReviewService:
    def __init__(self, session: AsyncSession): ...

    async def list_days(self, start: date, end: date) -> list[date]:
        # union: review_runs.trade_date + sector_rotation_snapshots.trade_date in range

    async def get_day(self, trade_date: date | None) -> ReviewDayResponse:
        day = ShortTermService.resolve_trade_date(trade_date)
        events = await self.repo.list_events(day)
        if events:
            return self._project_from_events(day, events, runs)
        return await self._project_from_legacy_snapshots(day)

    async def get_theme(self, theme_id: int, days: int = 10) -> ReviewThemeResponse: ...
```

**涨跌验证 `performance`：**  
对候选 `stock_id`，读 `stocks.rise_fall_pct` **仅当** `day == resolve_trade_date(None)`（当日）；历史日若无日行情表则 `same_day_pct=null`，`reason="无历史行情快照"`。  
次日：若存在 `day+1` 交易日的候选或信号表可关联则填；否则 `next_day_pct=null`。  
**禁止**用今日 live 填历史。

**阶段迁移：**  
有事件用 `sector_stage_change`；降级时对比 `sector_rotation_snapshots` 的 `day` vs 上一交易日 `lifecycle_stage`。

- [ ] **Step 4: 测试 PASS**

---

### Task 6: 日报 ReviewReportService + 后台任务（TDD）

**Files:** `review_report.py`、`review_report_scheduler.py`、`test_review_report_service.py`

- [ ] **Step 1: 规则摘要纯函数**

```python
def build_rule_summary(day: ReviewDayResponse) -> dict:
    # content_json: {summary, primary_strategy, candidate_count, stage_up_count, degraded}
    # content_md: 中文几段
```

- [ ] **Step 2: ensure 行为测试**

```python
@pytest.mark.asyncio
async def test_ensure_returns_existing_report():
    ...

@pytest.mark.asyncio
async def test_ensure_without_user_writes_rule_fallback():
    # user_id=None → status=rule_fallback，不调 LLM

@pytest.mark.asyncio
async def test_ensure_with_user_marks_pending_and_schedules():
    # mock create_task；返回 status=pending
```

- [ ] **Step 3: 实现**

```python
class ReviewReportService:
    async def get_report(self, trade_date, user_id) -> ReviewAiReport | None: ...

    async def ensure(self, trade_date, user_id: int | None) -> ReviewAiReportResponse:
        existing = await self.repo.get_report(trade_date, user_id)
        if existing and existing.status in ("success", "rule_fallback"):
            return to_response(existing)
        day = await ReviewService(self.session).get_day(trade_date)
        if user_id is None:
            return await self._save_rule(day, user_id=None)
        # 有用户：写 pending，asyncio.create_task(_generate_in_background(trade_date, user_id))
        # 立即返回 pending
        ...

async def _generate_in_background(trade_date: date, user_id: int) -> None:
    async with AsyncSessionLocal() as session:
        try:
            # ModelProviderService(session, user_id).adapter().complete(...)
            # 失败 → rule_fallback + error
        finally:
            await session.commit()
```

LLM prompt：仅注入日复盘 JSON 摘要；要求输出 `{summary, sections:{mainlines,candidates,risks}, markdown}`；解析失败 → fallback。

- [ ] **Step 4:** `review_report_scheduler.py` 可选：交易日 16:00 后对「昨日」写全局规则摘要；无配置则不在 lifespan 启动。Settings 增加 `REVIEW_REPORT_SCHEDULER_ENABLED: bool = False`（默认关，首开 ensure 已够用）。

---

### Task 7: API 路由

**Files:** `backend/app/api/review.py`、`main.py`、`tests/unit/test_review_api.py`

- [ ] **Step 1: 路由**

```python
router = APIRouter(prefix="/review", tags=["review"])

@router.get("/days")
async def list_review_days(from_date: date | None = Query(None, alias="from"), to_date: date | None = Query(None, alias="to"), db=Depends(get_db)):
    ...

@router.get("/days/{trade_date}")
async def get_review_day(trade_date: date, db=Depends(get_db)):
    return await ReviewService(db).get_day(trade_date)

@router.get("/themes/{theme_id}")
async def get_review_theme(theme_id: int, days: int = 10, db=Depends(get_db)):
    ...

@router.get("/days/{trade_date}/report")
async def get_review_report(trade_date: date, db=Depends(get_db), user: User | None = Depends(get_optional_user)):
    # 若无 get_optional_user：未登录只查 user_id=None；登录查用户报告否则回落规则摘要
    ...

@router.post("/days/{trade_date}/report/ensure")
async def ensure_review_report(trade_date: date, db=Depends(get_db), user: User | None = Depends(get_optional_user)):
    ...
```

若项目无 `get_optional_user`，在 `app/core/auth.py` 增加：Bearer 缺失返回 `None`，无效 token 返回 `None` 或 401（建议缺失→None，坏 token→401）。

- [ ] **Step 2: `main.py`**

```python
from app.api.review import router as review_router
app.include_router(review_router, prefix="/api/v1")
```

- [ ] **Step 3: API 单测** — patch `ReviewService.get_day` / `ReviewReportService.ensure`，断言路径与 200。

---

### Task 8: Frontend API + 类型

**Files:** `frontend/src/types/review.ts`、`frontend/src/api/review.ts`、`review.test.ts`

- [ ] **Step 1: 类型与 client**

```ts
export function fetchReviewDays(params: { from?: string; to?: string }) { ... }
export function fetchReviewDay(date: string) {
  return apiClient.get<ReviewDayResponse>(`/review/days/${date}`)
}
export function fetchReviewTheme(themeId: number, days = 10) { ... }
export function fetchReviewReport(date: string) { ... }
export function ensureReviewReport(date: string) {
  return apiClient.post<ReviewReportResponse>(`/review/days/${date}/report/ensure`, null, { timeout: 60_000 })
}
```

- [ ] **Step 2: Vitest** — mock axios，断言 URL。

---

### Task 9: Frontend 复盘页 + Nav

**Files:** `CardNav.tsx`、`AppCardNav.tsx`、`App.tsx`、`features/review/*`、对应测试

- [ ] **Step 1: 扩展 tone**

```ts
export type CardNavTone = 'dashboard' | 'analysis' | 'settings' | 'review'
// NAV_CARD_SURFACE 增加 review: 冷灰绿或石板色，避免紫/奶油套路
```

- [ ] **Step 2: Nav 项**

```ts
{
  label: '复盘研究',
  tone: 'review',
  links: [
    { label: '复盘台', href: '/review', ariaLabel: '进入复盘台' },
  ],
},
```

放在「题材分析」与「设置」之间。更新 `AppCardNav.test.tsx`：打开菜单可见「复盘研究」与 `href="/review"`。

- [ ] **Step 3: `App.tsx`**

```tsx
const ReviewDesk = lazy(() =>
  import('@/features/review/ReviewDesk').then((m) => ({ default: m.ReviewDesk }))
)
// <Route path="/review" element={<PageLayout><ReviewDesk /></PageLayout>} />
```

- [ ] **Step 4: `ReviewDesk` UI**

- 顶栏：模式 Toggle「交易日 | 题材」；日期 `<input type="date">` 或按钮切换最近日；题材模式用搜索/数字 id（可先 themeId query）
- `useQuery` 拉 `fetchReviewDay`；`useEffect` 成功后 `ensureReviewReport`（或独立 mutation），`pending/running` 时 2s 轮询 `fetchReviewReport`
- 区块：降级条 → runs 时间线 → 策略卡只读 → 候选表 → 阶段迁移列表 → performance → `ReviewReportPanel`
- 题材模式：`ReviewThemePanel` + 点击某日 `setSearchParams({ date })` 切回交易日

- [ ] **Step 5: 测试**

```tsx
it('renders day mode degraded banner and strategy section', async () => {
  // mock fetchReviewDay degraded + strategy_card
})
it('nav link to review exists', ...) // 已在 AppCardNav
```

---

### Task 10: 本地迁移 + 冒烟

- [ ] **Step 1:**

```bash
cd backend
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m pytest tests/unit/test_review_models.py tests/unit/test_review_events.py tests/unit/test_review_service.py tests/unit/test_review_report_service.py tests/unit/test_review_api.py -q
```

- [ ] **Step 2:**

```bash
cd frontend
pnpm exec vitest run src/api/review.test.ts src/features/review/ReviewDesk.test.tsx src/components/AppCardNav.test.tsx
```

- [ ] **Step 3: 手工**

1. 打开 Nav → 复盘研究 → 复盘台，URL 为 `/review`，首页 `/` 仍是看板  
2. 触发一次 short-term analyze/refresh 后，复盘日可见 runs/事件或至少 degraded 投影  
3. 未登录 ensure → 规则摘要；登录有模型 → pending→success（或 fallback）

---

## Spec coverage checklist

| Spec 项 | Task |
|---------|------|
| 三表迁移 + ORM | 1–2 |
| run + 实体事件写入 | 3–4 |
| 日聚合 / 题材轴 / 无事件降级 | 5 |
| 涨跌验证不伪造历史 | 5 |
| 日报 ensure + 后台 + 规则降级 | 6–7 |
| `/api/v1/review/*` | 7 |
| Nav「复盘研究」仅复盘台 + `/review` | 9 |
| 双模式 UI | 9 |
| 不实现催化/挖掘/图谱/自选 | —（范围外） |
| Worker 不堵读 API | 6 |

## Placeholder / 一致性自检

- 迁移号 **016**（接 015），与计划内文件名一致  
- `event_type` 与 spec 枚举一致：`strategy_card` / `candidate_upsert` / `sector_stage_change` / `emotion_snapshot` / `signal_batch` / `quote_refresh`  
- 无空链 Nav；tone 扩展为 `review`  
- 提交仅用户要求时执行  

---

## 执行交接

Plan complete and saved to `docs/superpowers/plans/2026-07-26-review-desk-event-sourcing.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — 每任务派生子代理，任务间复查  
2. **Inline Execution** — 本会话按任务推进，关键检查点暂停  

Which approach?
