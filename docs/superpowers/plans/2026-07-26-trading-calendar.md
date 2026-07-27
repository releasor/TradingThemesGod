# A 股交易日历 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 AKShare 开市日落库，全站 `resolve_trade_date`（含节假日）与设置页一键同步一致。

**Architecture:** `trading_calendar_days` + `trading_calendar_meta` 落库；同步后把开市日载入进程内 `frozenset`，`TradingCalendar.resolve` 保持同步 API，供现有 `ShortTermService.resolve_trade_date` 委托。启动 lifespan 按需同步；设置页 `POST /sync` 强制刷新。空库/失败时周末兜底并 `degraded`。

**Tech Stack:** FastAPI、SQLAlchemy、Alembic、AKShare、React + TanStack Query、Vitest/pytest

**Spec:** `docs/superpowers/specs/2026-07-26-trading-calendar-design.md`

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/alembic/versions/020_create_trading_calendar_tables.py` | 迁移 |
| `backend/app/models/trading_calendar.py` | ORM |
| `backend/app/repositories/trading_calendar.py` | 读写 days + meta |
| `backend/app/services/trading_calendar.py` | 内存日历 + resolve/previous/list |
| `backend/app/services/trading_calendar_sync.py` | AKShare 拉取 + upsert + 刷新内存 |
| `backend/app/schemas/trading_calendar.py` | status / resolve DTO |
| `backend/app/api/market_calendar.py` | status / resolve / sync |
| `backend/app/main.py` | 注册路由 + lifespan 按需同步 |
| `backend/app/services/short_term.py` | `resolve_trade_date` / `_period_trade_dates` 委托 |
| `backend/app/services/review.py` | `_previous_weekday` / `_next_weekday` 用日历 |
| `backend/app/services/first_to_second.py` | 昨交易日用日历 |
| `frontend/src/types/trading-calendar.ts` | 类型 |
| `frontend/src/api/trading-calendar.ts` | API 客户端 |
| `frontend/src/features/settings/TradingCalendarSettings.tsx` | 设置页 |
| `frontend/src/lib/marketClock.ts` | 接 status |
| `frontend/src/features/review/ReviewDesk.tsx` | resolve API |
| `frontend/src/components/SettingsSubnav.tsx` / `AppCardNav.tsx` / `App.tsx` | 路由与导航 |

---

### Task 1: 迁移 + ORM

**Files:**
- Create: `backend/alembic/versions/020_create_trading_calendar_tables.py`
- Create: `backend/app/models/trading_calendar.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/unit/test_trading_calendar_models.py`

- [ ] **Step 1: Write the failing model test**

```python
"""trading_calendar ORM 表名与约束。"""

from app.models.trading_calendar import TradingCalendarDay, TradingCalendarMeta


def test_day_tablename_and_pk():
    assert TradingCalendarDay.__tablename__ == "trading_calendar_days"
    cols = {c.name for c in TradingCalendarDay.__table__.columns}
    assert {"trade_date", "source", "synced_at"} <= cols


def test_meta_tablename():
    assert TradingCalendarMeta.__tablename__ == "trading_calendar_meta"
    cols = {c.name for c in TradingCalendarMeta.__table__.columns}
    assert {"id", "last_synced_at", "row_count", "min_date", "max_date", "last_error"} <= cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .\.venv\Scripts\python.exe -m pytest tests/unit/test_trading_calendar_models.py -q`  
Expected: FAIL import error

- [ ] **Step 3: Implement migration + ORM**

Migration `020` (`down_revision = "019_create_mainline_graph_tables"`):

```python
"""创建 trading_calendar_days / trading_calendar_meta。"""

import sqlalchemy as sa
from alembic import op

revision = "020_create_trading_calendar_tables"
down_revision = "019_create_mainline_graph_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trading_calendar_days",
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("trade_date"),
        comment="A股开市日",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_table(
        "trading_calendar_meta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_date", sa.Date(), nullable=True),
        sa.Column("max_date", sa.Date(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="交易日历同步元信息",
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.execute(
        "INSERT INTO trading_calendar_meta (id, source, row_count) VALUES (1, 'akshare_sina', 0)"
    )


def downgrade() -> None:
    op.drop_table("trading_calendar_meta")
    op.drop_table("trading_calendar_days")
```

ORM (`backend/app/models/trading_calendar.py`) — 对齐现有 Mapped 风格；导出到 `__init__.py`。

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_trading_calendar_models.py -q`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/020_create_trading_calendar_tables.py backend/app/models/trading_calendar.py backend/app/models/__init__.py backend/tests/unit/test_trading_calendar_models.py
git commit -m "feat(calendar): add trading calendar tables and ORM"
```

---

### Task 2: Repository + 内存 TradingCalendar 解析

**Files:**
- Create: `backend/app/repositories/trading_calendar.py`
- Create: `backend/app/services/trading_calendar.py`
- Test: `backend/tests/unit/test_trading_calendar_service.py`

- [ ] **Step 1: Write failing resolve tests**

```python
"""TradingCalendar 开市日解析与周末/节假日回退。"""

from datetime import date

from app.services.trading_calendar import TradingCalendar


def setup_function():
    TradingCalendar.clear()


def test_resolve_holiday_monday_rolls_to_prior_friday():
    # 模拟 2026-10-01~07 休市，09-30 开市，10-08 开市
    TradingCalendar.load_dates(
        {
            date(2026, 9, 30),
            date(2026, 10, 8),
            date(2026, 10, 9),
        }
    )
    assert TradingCalendar.resolve(date(2026, 10, 5)) == date(2026, 9, 30)
    assert TradingCalendar.is_trade_day(date(2026, 10, 5)) is False
    assert TradingCalendar.previous_trade_day(date(2026, 10, 8)) == date(2026, 9, 30)


def test_resolve_weekend_with_calendar():
    TradingCalendar.load_dates({date(2026, 7, 24), date(2026, 7, 27)})
    assert TradingCalendar.resolve(date(2026, 7, 25)) == date(2026, 7, 24)


def test_empty_calendar_weekend_fallback_degraded():
    TradingCalendar.clear()
    assert TradingCalendar.resolve(date(2026, 7, 26)) == date(2026, 7, 24)
    assert TradingCalendar.degraded is True


def test_list_trade_days_in_range():
    TradingCalendar.load_dates(
        {date(2026, 7, 22), date(2026, 7, 23), date(2026, 7, 24), date(2026, 7, 27)}
    )
    assert TradingCalendar.list_trade_days(date(2026, 7, 23), date(2026, 7, 27)) == [
        date(2026, 7, 23),
        date(2026, 7, 24),
        date(2026, 7, 27),
    ]
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `.\.venv\Scripts\python.exe -m pytest tests/unit/test_trading_calendar_service.py -q`

- [ ] **Step 3: Implement service + repository**

`TradingCalendar`（进程单例状态）：

```python
class TradingCalendar:
    _days: frozenset[date] = frozenset()
    _min: date | None = None
    _max: date | None = None
    degraded: bool = True

    @classmethod
    def clear(cls) -> None:
        cls._days = frozenset()
        cls._min = cls._max = None
        cls.degraded = True

    @classmethod
    def load_dates(cls, days: set[date] | frozenset[date]) -> None:
        cls._days = frozenset(days)
        cls._min = min(days) if days else None
        cls._max = max(days) if days else None
        cls.degraded = not bool(days)

    @classmethod
    def is_trade_day(cls, d: date) -> bool:
        if cls._days:
            return d in cls._days
        return d.weekday() < 5

    @classmethod
    def resolve(cls, trade_date: date | None = None) -> date:
        from datetime import timedelta
        # today: Asia/Shanghai
        base = trade_date or _shanghai_today()
        if cls._days:
            steps = 0
            while base not in cls._days and steps < 400:
                base -= timedelta(days=1)
                steps += 1
                if cls._min and base < cls._min - timedelta(days=14):
                    break
            if base in cls._days:
                return base
        # weekend fallback
        while base.weekday() >= 5:
            base -= timedelta(days=1)
        return base

    @classmethod
    def previous_trade_day(cls, d: date) -> date:
        from datetime import timedelta
        cursor = d - timedelta(days=1)
        return cls.resolve(cursor) if cursor in cls._days or not cls._days else cls.resolve(cursor)

    @classmethod
    def list_trade_days(cls, start: date, end: date) -> list[date]:
        if cls._days:
            return sorted(x for x in cls._days if start <= x <= end)
        from datetime import timedelta
        out: list[date] = []
        cur = start
        while cur <= end:
            if cur.weekday() < 5:
                out.append(cur)
            cur += timedelta(days=1)
        return out
```

Repository methods: `replace_all(dates, source)`, `list_all_dates()`, `get_meta()`, `upsert_meta(...)`, `ensure_meta_row()`.

`previous_trade_day` 精确定义：返回严格 `< d` 的最大开市日；空库时用 resolve(d-1) 的周末逻辑。

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(calendar): add in-memory TradingCalendar resolve"
```

---

### Task 3: Sync service（mock AKShare）

**Files:**
- Create: `backend/app/services/trading_calendar_sync.py`
- Test: `backend/tests/unit/test_trading_calendar_sync.py`

- [ ] **Step 1: Write failing sync test**

```python
@pytest.mark.asyncio
async def test_sync_replaces_days_and_refreshes_memory(monkeypatch):
    session = AsyncMock()
    repo = AsyncMock()
    repo.replace_all = AsyncMock(return_value=3)
    repo.list_all_dates = AsyncMock(
        return_value=[date(2026, 7, 22), date(2026, 7, 23), date(2026, 7, 24)]
    )
    repo.upsert_meta = AsyncMock()

    def fake_fetch():
        return [date(2026, 7, 22), date(2026, 7, 23), date(2026, 7, 24)]

    monkeypatch.setattr(
        "app.services.trading_calendar_sync.fetch_akshare_trade_dates",
        fake_fetch,
    )
    from app.services.trading_calendar_sync import TradingCalendarSyncService
    from app.services.trading_calendar import TradingCalendar

    TradingCalendar.clear()
    svc = TradingCalendarSyncService(session)
    svc.repo = repo
    status = await svc.sync(force=True)
    assert status.row_count == 3
    assert TradingCalendar.is_trade_day(date(2026, 7, 24))
    assert TradingCalendar.degraded is False
```

另加：`test_sync_failure_keeps_old_meta_error`（fetch raise → `last_error` 写入、不 clear days）。

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement sync**

```python
def fetch_akshare_trade_dates() -> list[date]:
    import akshare as ak
    frame = ak.tool_trade_date_hist_sina()
    # 列名通常为 trade_date；解析为 date 列表
    ...

class TradingCalendarSyncService:
    async def sync(self, *, force: bool = False) -> TradingCalendarStatus:
        # 若 not force 且 last_synced_at 在 24h 内 → 仅 reload_memory_from_db，返回 status
        # else: asyncio.to_thread(fetch_akshare_trade_dates)
        # repo.replace_all + upsert_meta + TradingCalendar.load_dates
        # on error: upsert_meta(last_error=...) ; re-raise or return degraded status

    async def reload_memory(self) -> None:
        dates = await self.repo.list_all_dates()
        TradingCalendar.load_dates(set(dates))

    async def maybe_sync_on_startup(self) -> None:
        try:
            await self.sync(force=False)
        except Exception as exc:
            logger.warning("交易日历启动同步失败", error=str(exc))
            await self.reload_memory()
```

`replace_all`：delete all days + bulk insert（同事务）。

- [ ] **Step 4: PASS + Commit**

```bash
git commit -m "feat(calendar): sync AKShare trade dates into DB"
```

---

### Task 4: Schemas + API + lifespan

**Files:**
- Create: `backend/app/schemas/trading_calendar.py`
- Create: `backend/app/api/market_calendar.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/unit/test_market_calendar_api.py`

- [ ] **Step 1: Write API tests with TestClient / AsyncMock service**

Endpoints:

- `GET /api/v1/market/calendar/status` — 公开只读  
- `GET /api/v1/market/calendar/resolve?date=2026-10-05` — 公开只读  
- `POST /api/v1/market/calendar/sync` — `Depends(get_current_user)`

Status schema 字段对齐 spec：`last_synced_at`, `row_count`, `min_date`, `max_date`, `last_error`, `degraded`, `today_is_trade_day`, `data_trade_date`, `source`。

- [ ] **Step 2: Implement router + register in main.py**

```python
router = APIRouter(prefix="/market/calendar", tags=["market-calendar"])
```

lifespan 在 scrapers 注册后：

```python
async def _calendar_startup():
    async with AsyncSessionLocal() as session:
        await TradingCalendarSyncService(session).maybe_sync_on_startup()
        await session.commit()

asyncio.create_task(_calendar_startup())
```

- [ ] **Step 3: PASS + Commit**

```bash
git commit -m "feat(calendar): expose market calendar status resolve sync APIs"
```

---

### Task 5: 接线 ShortTerm / Review / FirstToSecond

**Files:**
- Modify: `backend/app/services/short_term.py`（`resolve_trade_date`、`_period_trade_dates`；`get_sectors` / `_refresh_quotes_overview` 缺省日也走 resolve）
- Modify: `backend/app/services/review.py`（`_previous_weekday` / `_next_weekday` → `TradingCalendar.previous_trade_day` / 下一开市日）
- Modify: `backend/app/services/first_to_second.py`
- Update: `backend/tests/unit/test_short_term_service.py::test_resolve_trade_date_rolls_weekend_to_previous_friday`
- Add: holiday case using `TradingCalendar.load_dates`

- [ ] **Step 1: Update failing expectation tests for holiday**

```python
def test_resolve_trade_date_uses_trading_calendar_holidays():
    from app.services.trading_calendar import TradingCalendar
    TradingCalendar.load_dates({date(2026, 9, 30), date(2026, 10, 8)})
    assert ShortTermService.resolve_trade_date(date(2026, 10, 1)) == date(2026, 9, 30)
```

- [ ] **Step 2: Change resolve body**

```python
@staticmethod
def resolve_trade_date(trade_date: date | None = None) -> date:
    from app.services.trading_calendar import TradingCalendar
    return TradingCalendar.resolve(trade_date)
```

`_period_trade_dates` → `TradingCalendar.list_trade_days(start, end)`。

`review._previous_weekday` → `TradingCalendar.previous_trade_day`。  
下一开市日：从 `d+1` 起向前找第一个 `is_trade_day`（可加 `TradingCalendar.next_trade_day`）。

- [ ] **Step 3: Run related unit tests PASS + Commit**

```bash
git commit -m "feat(calendar): wire resolve_trade_date to TradingCalendar"
```

---

### Task 6: Frontend API + 设置页

**Files:**
- Create: `frontend/src/types/trading-calendar.ts`
- Create: `frontend/src/api/trading-calendar.ts`
- Create: `frontend/src/api/trading-calendar.test.ts`
- Create: `frontend/src/features/settings/TradingCalendarSettings.tsx`
- Modify: `frontend/src/components/SettingsSubnav.tsx`
- Modify: `frontend/src/components/AppCardNav.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: API client + vitest mock**

```typescript
export async function fetchCalendarStatus(): Promise<TradingCalendarStatus> {
  const { data } = await apiClient.get<TradingCalendarStatus>('/market/calendar/status')
  return data
}

export async function resolveTradeDate(date?: string): Promise<TradingCalendarResolve> {
  const { data } = await apiClient.get<TradingCalendarResolve>('/market/calendar/resolve', {
    params: date ? { date } : {},
  })
  return data
}

export async function syncTradingCalendar(): Promise<TradingCalendarStatus> {
  const { data } = await apiClient.post<TradingCalendarStatus>('/market/calendar/sync', null, {
    timeout: 120_000,
  })
  return data
}
```

- [ ] **Step 2: Settings page**

GlowCard：显示 `data_trade_date`、覆盖区间、`last_synced_at`、`last_error`、`degraded`；按钮「同步交易日历」调 `syncTradingCalendar`（需登录，无 token 提示去登录）。

- [ ] **Step 3: Nav + route `/settings/calendar`**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(calendar): add settings page and calendar API client"
```

---

### Task 7: marketClock + ReviewDesk

**Files:**
- Modify: `frontend/src/lib/marketClock.ts`
- Modify: `frontend/src/features/review/ReviewDesk.tsx`
- Test: `frontend/src/features/review/ReviewDesk.test.tsx`；若有 `marketClock` 测试一并更新

- [ ] **Step 1: marketClock**

增加可选参数或模块级缓存：

```typescript
let calendarOverride: { isTradingDay: boolean; dataTradeDate: string } | null = null

export function setMarketCalendarOverride(v: {...} | null) { calendarOverride = v }

export function getMarketClockInfo(now = new Date()): MarketClockInfo {
  // 若 calendarOverride：用其 isTradingDay / dataTradeDate
  // 否则保留周末逻辑兜底
}
```

在 `MarketStatusNav`（或 App 根）`useQuery(['market','calendar','status'])` 成功后 `setMarketCalendarOverride`。

- [ ] **Step 2: ReviewDesk**

`resolveTradeDateIso`：本地周末仍作即时 UI；挂载后 `resolveTradeDate(dateParam)`，若返回不同则 `setSearchParams`。或 day 查询 key 直接用后端 `trade_date`（已有 sync effect）——确保请求前用 `resolve` API：

```typescript
const resolvedQuery = useQuery({
  queryKey: ['market', 'calendar', 'resolve', dateParam],
  queryFn: () => resolveTradeDate(dateParam ?? undefined),
})
const tradeDate = resolvedQuery.data?.trade_date ?? resolveTradeDateIso(dateParam)
```

- [ ] **Step 3: Tests PASS + Commit**

```bash
git commit -m "feat(calendar): use server calendar in marketClock and review desk"
```

---

### Task 8: 迁移执行 + 冒烟

- [ ] **Step 1: Run alembic upgrade**

```bash
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

- [ ] **Step 2: 单元回归**

```bash
.\.venv\Scripts\python.exe -m pytest tests/unit/test_trading_calendar_models.py tests/unit/test_trading_calendar_service.py tests/unit/test_trading_calendar_sync.py tests/unit/test_market_calendar_api.py tests/unit/test_short_term_service.py -q
```

- [ ] **Step 3: 前端**

```bash
cd frontend
pnpm exec vitest run src/api/trading-calendar.test.ts src/features/review/ReviewDesk.test.tsx
```

- [ ] **Step 4: 手动冒烟**

1. 启动 API → 日志可见日历同步或加载  
2. `GET /api/v1/market/calendar/status` 有 `row_count > 0`  
3. 设置页同步按钮成功  
4. 复盘台选周末/已知节假日回退到上一开市日  

- [ ] **Step 5: Final commit if needed**

```bash
git commit -m "test(calendar): finish trading calendar smoke coverage"
```

---

## Spec coverage checklist

| Spec 项 | Task |
|---------|------|
| 表 days + meta | 1 |
| TradingCalendar resolve / previous / list | 2 |
| AKShare sync + 24h + force | 3–4 |
| API status/resolve/sync | 4 |
| lifespan 按需同步 | 4 |
| 接线 short_term/review/first_to_second | 5 |
| 设置页 | 6 |
| marketClock + ReviewDesk | 7 |
| 空库周末兜底 degraded | 2, 4 |
| 无单日手改 | （不做） |

## Self-review notes

- 无 TBD/placeholder；`previous_trade_day` / `next_trade_day` 在 Task 2/5 定义清楚。  
- `resolve_trade_date` 保持 **同步**，依赖内存日历，避免全链路 async 改造。  
- sync 鉴权：`get_current_user`；status/resolve 公开，与「市场只读」一致。  
