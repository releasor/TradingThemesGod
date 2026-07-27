# 题材生命周期与短线雷达全量落地 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地短线日信号全量表与采集/规则引擎，为题材打上五阶段生命周期与四维强度，并在看板雷达、题材卡/库、详情页完整展示。

**Architecture:** 扩展现有 `/api/v1/short-term`：采集写入 `daily_stock_signals` / `dragon_tiger_entries`，`SectorRotationService` 写入含生命周期字段的 `sector_rotation_snapshots`，一进二写入 `short_term_candidates`；overview/sectors/lifecycle 优先读库；题材 list/detail join 最近交易日阶段与强度。前端补齐雷达区块 + 徽章/仪表/轨迹。

**Tech Stack:** FastAPI、SQLAlchemy Async、Alembic、MySQL 8、pytest、React、TanStack Query、Vitest、Tailwind、ECharts（轨迹）。

**Spec:** `docs/superpowers/specs/2026-07-25-theme-lifecycle-short-term-radar-design.md`  
**Supersedes (for this delivery):** `docs/superpowers/plans/2026-07-21-short-term-opportunity-radar.md`（表与雷达 UI 未完全落地部分并入本计划；已有现算 overview/一进二代码在本计划中改为读库并扩展）

**Commits:** 仅在用户明确要求时提交；步骤中的 commit 为建议信息，默认不自动执行。

---

## 文件结构

### 新建

| 文件 | 职责 |
|------|------|
| `backend/alembic/versions/015_create_short_term_radar_tables.py` | 五表 + 生命周期/强度列 |
| `backend/app/models/short_term_signal.py` | ORM：五表 |
| `backend/app/repositories/short_term_signal.py` | 幂等写入与按日查询 |
| `backend/app/scrapers/short_term_signals.py` | 涨停/炸板等解析（可注入 provider） |
| `backend/app/scrapers/dragon_tiger.py` | 龙虎榜解析 |
| `backend/app/services/sector_rotation.py` | 轮动分 + 生命周期 + 四维强度 |
| `backend/app/services/lifecycle_rules.py` | 纯函数：阶段与四维（易单测） |
| `backend/tests/unit/test_short_term_models.py` | 表/索引 |
| `backend/tests/unit/test_lifecycle_rules.py` | 阶段与四维 |
| `backend/tests/unit/test_sector_rotation_service.py` | 落库编排 |
| `backend/tests/unit/test_short_term_signal_scraper.py` | 采集解析 |
| `frontend/src/components/short-term/ShortTermRadarSection.tsx` | 雷达总入口 |
| `frontend/src/components/short-term/ShortTermOverviewPanel.tsx` | 展望/结论/降级 |
| `frontend/src/components/short-term/SectorRotationPanel.tsx` | 主线列表+阶段 |
| `frontend/src/components/short-term/ShortTermRuleBadges.tsx` | 规则徽章 |
| `frontend/src/components/ThemeLifecycleBadge.tsx` | 阶段徽章 |
| `frontend/src/components/ThemeStrengthGauge.tsx` | 四维仪表 |
| `frontend/src/components/charts/ThemeLifecycleTrend.tsx` | 近 10 日轨迹 |
| 对应 `*.test.tsx` / `*.test.ts` | 组件与 API 测 |

### 修改

| 文件 | 变更 |
|------|------|
| `backend/app/models/__init__.py` | 注册五模型 |
| `backend/app/schemas/short_term.py` | sectors/lifecycle/refresh run、扩展 overview |
| `backend/app/schemas/theme.py` | `ThemeBrief` 等增加可选生命周期字段 |
| `backend/app/services/short_term.py` | 编排 refresh；overview 读库 |
| `backend/app/services/short_term_rules.py` | 读信号表增强一进二 |
| `backend/app/services/first_to_second.py` | 优先读 `short_term_candidates` |
| `backend/app/api/short_term.py` | `POST /signals/refresh`、`GET /sectors`、`GET /themes/{id}/lifecycle` |
| `backend/app/api/theme.py` / theme service/repo | list/ranking/detail join 快照 |
| `backend/tests/unit/test_short_term_*.py` | 扩展现有测 |
| `frontend/src/types/short-term.ts` / `theme.ts` | 类型 |
| `frontend/src/api/short-term.ts` | 新接口 |
| `frontend/src/features/dashboard/ThemeDashboard.tsx` | 雷达区块 + 紧凑布局 |
| `frontend/src/components/ThemeCard.tsx` | 徽章+强度 |
| `frontend/src/features/themes/ThemeLibrary.tsx` | 阶段列+筛选 |
| `frontend/src/features/themes/ThemeDetail.tsx` | 仪表+轨迹 |
| `frontend/src/components/AppCardNav.tsx` | 可选看板锚点「短线雷达」 |

### 已有可复用

- `backend/app/services/short_term.py`、`short_term_rules.py`、`first_to_second.py`
- `frontend/.../MarketStrategyCard.tsx`、`BoardUpgradeReference.tsx`
- `theme_market_snapshots` 广度字段

---

### Task 1: 迁移 + ORM 五表

**Files:** `015_create_short_term_radar_tables.py`、`short_term_signal.py`、`models/__init__.py`、`test_short_term_models.py`

- [ ] **Step 1: 写失败的模型测试**

```python
from app.models.short_term_signal import (
    DailyStockSignal,
    DragonTigerEntry,
    SectorRotationSnapshot,
    ShortTermCandidate,
    ShortTermSignalRun,
)

def test_sector_rotation_has_lifecycle_columns():
    cols = {c.name for c in SectorRotationSnapshot.__table__.columns}
    assert "lifecycle_stage" in cols
    assert "strength_score" in cols
    assert "limit_quality_score" in cols
    assert "flow_score" in cols
    assert "leader_clarity_score" in cols
    assert "breadth_score" in cols
    assert "score_breakdown" in cols
    assert "degraded" in cols
    assert "missing_metrics" in cols

def test_daily_stock_signal_indexes():
    names = {i.name for i in DailyStockSignal.__table__.indexes}
    assert "idx_daily_stock_signals_date_type" in names
    assert "idx_daily_stock_signals_date_stock" in names
    assert "idx_daily_stock_signals_date_theme" in names
```

- [ ] **Step 2: 运行确认失败**

```bash
cd backend
pytest tests/unit/test_short_term_models.py -q
```

Expected: import/表不存在而失败。

- [ ] **Step 3: 实现 ORM**

按 spec 字段建五表；`SectorRotationSnapshot.lifecycle_stage` 用 `String(32)`；分数用 `Integer` 可空（`flow_score`）；`score_breakdown`/`missing_metrics`/`matched_rules` 等用 `JSON`；FK `ondelete=CASCADE` 到 `stocks`/`themes`。

- [ ] **Step 4: Alembic `015`**

`down_revision = "014_create_stock_ai_reports"`；`upgrade` 建五表与索引；`downgrade` 反序 drop。

- [ ] **Step 5: 注册 `__init__.py` 并跑测**

```bash
pytest tests/unit/test_short_term_models.py -q
```

Expected: PASS。本地可 `alembic upgrade head`（有 DB 时）。

---

### Task 2: Repository 幂等写入

**Files:** `repositories/short_term_signal.py`、`tests/unit/test_short_term_signal_repository.py`

- [ ] **Step 1: 失败测试** — `upsert_signals`、`upsert_dragon_tiger`、`upsert_sector_snapshots`、`upsert_candidates`、`create_run`/`finish_run`；同键二次写入不增行。

- [ ] **Step 2: 实现 repository** — 使用 MySQL `ON DUPLICATE KEY` 或先 select 再 update；查询：`list_signals(trade_date, theme_id?)`、`list_snapshots(trade_date)`、`list_lifecycle_history(theme_id, days=10)`、`get_candidates(trade_date, strategy)`。

- [ ] **Step 3: 跑测 PASS**

```bash
pytest tests/unit/test_short_term_signal_repository.py -q
```

---

### Task 3: 生命周期与四维纯规则（TDD）

**Files:** `services/lifecycle_rules.py`、`tests/unit/test_lifecycle_rules.py`

- [ ] **Step 1: 写失败测试（固定 fixture 输入 → 阶段/分数）**

覆盖：

1. 高潮：近 3 日高涨停 + strength≥70  
2. 分歧：涨停家数↓≥30% 且曾发酵  
3. 退潮：双降 + strength&lt;40  
4. 发酵：斜率向上未达高潮  
5. 萌芽：默认弱信号  
6. 缺回流：`flow_score is None`，总分用 35/35/30 权重，`missing_metrics == ["flow"]`

输入结构建议：

```python
@dataclass
class ThemeDayMetrics:
    trade_date: date
    heat_index: float
    rise_fall_pct: float
    stock_count: int
    up_count: int
    down_count: int
    flat_count: int
    suspended_count: int
    limit_up_count: int
    failed_limit_up_count: int
    one_word_count: int
    streak_ge2_count: int
    leader_rise_fall_pct: float | None
    avg_rise_fall_pct: float | None
    second_rise_fall_pct: float | None
    dragon_net_amount: float | None  # None = 缺失
    theme_net_percentile: float | None  # 0-1，有回流时
```

- [ ] **Step 2: 实现 `compute_strength` + `compute_lifecycle` + `build_snapshot_scores`** — 阈值做成模块级常量（`CLIMAX_STRENGTH_MIN = 70` 等），与 spec 一致。

- [ ] **Step 3: 跑测 PASS**

```bash
pytest tests/unit/test_lifecycle_rules.py -q
```

---

### Task 4: 采集器（可注入 provider）

**Files:** `scrapers/short_term_signals.py`、`scrapers/dragon_tiger.py`、`test_short_term_signal_scraper.py`

- [ ] **Step 1: Fixture 解析测试** — 给定固定 JSON/字典列表，断言产出的 signal_type、`is_failed`、`streak_days`、龙虎 `net_amount`。

- [ ] **Step 2: 实现 scraper** — 默认对接现有公开源（可与 `first_to_second` / AkShare 路径对齐）；构造函数注入 `fetch_limit_pool` / `fetch_dragon_tiger` 便于测。失败抛明确异常或返回 `SourceResult(success=False, error=...)`，由编排层记入 `source_status`。

- [ ] **Step 3: 跑测 PASS**

---

### Task 5: SectorRotation + ShortTerm 编排 refresh

**Files:** `services/sector_rotation.py`、`services/short_term.py`、`services/first_to_second.py`、`services/short_term_rules.py`、对应测试

- [ ] **Step 1: `SectorRotationService.rebuild(trade_date)`**  
  - 题材集合 = 热度 Top100 ∪ 涨幅 Top100 ∪ 当日有信号题材  
  - 聚合成 `ThemeDayMetrics` 历史窗 → 调 `lifecycle_rules` → upsert snapshots  

- [ ] **Step 2: `ShortTermService.refresh_signals(trade_date, user?)`**  
  - 开 run → 采集 signals → 采集龙虎 →（可选）确保行情快照 → rebuild sectors → 跑一进二写 candidates → finish run  
  - 任一步源失败：`status=partial`，继续后续可执行步骤  

- [ ] **Step 3: `get_overview` / `get_sectors`** 优先读当日（或最近）snapshots + candidates 计数；无快照时保留现算降级并 `degraded=true`  

- [ ] **Step 4: `FirstToSecondService`** 有 candidates 行则组装为现有 `FirstToSecondCandidateResponse`；否则现算 + degraded  

- [ ] **Step 5: 单测** — mock repo/scraper；partial 龙虎；analyze 不调外网  

```bash
pytest tests/unit/test_sector_rotation_service.py tests/unit/test_short_term_service.py -q
```

---

### Task 6: API

**Files:** `api/short_term.py`、theme schemas/API、集成或 API 单测

- [ ] **Step 1: 新增路由**

```python
@router.post("/signals/refresh")
async def refresh_signals(
    trade_date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ...

@router.get("/sectors")
async def list_sectors(trade_date: date | None = Query(default=None), ...):
    ...

@router.get("/themes/{theme_id}/lifecycle")
async def theme_lifecycle(
    theme_id: int,
    days: int = Query(default=10, ge=1, le=60),
    ...
):
    ...
```

- [ ] **Step 2: `overview/refresh-data`** 内部调用 `refresh_signals` 逻辑后返回 overview（保持兼容）  

- [ ] **Step 3: ThemeBrief / Detail** 增加可选：

```python
lifecycle_stage: Literal["germination","fermentation","climax","divergence","ebb"] | None = None
strength_score: int | None = None
lifecycle_confidence: int | None = None
```

Theme list/ranking/detail service left join 最近 `sector_rotation_snapshots`。

- [ ] **Step 4: API 测试** — 401 refresh；200 sectors 含 stage；lifecycle 空历史返回 `[]` + 不 500  

```bash
pytest tests/unit/test_short_term_api.py tests/integration/test_short_term_api.py -q
```

（若无 integration 环境则仅 unit + TestClient）

---

### Task 7: 前端类型与 API client

**Files:** `types/short-term.ts`、`types/theme.ts`、`api/short-term.ts`、`api/short-term.test.ts`

- [ ] **Step 1: 类型**

```ts
export type LifecycleStage =
  | 'germination'
  | 'fermentation'
  | 'climax'
  | 'divergence'
  | 'ebb'

export interface SectorRotationItem {
  theme_id: number
  theme_name: string
  lifecycle_stage: LifecycleStage
  strength_score: number
  mainline_score: number
  limit_up_count: number
  degraded: boolean
  missing_metrics: string[]
}

export interface LifecyclePoint {
  trade_date: string
  lifecycle_stage: LifecycleStage
  strength_score: number
  limit_quality_score: number | null
  flow_score: number | null
  leader_clarity_score: number | null
  breadth_score: number | null
}
```

`ThemeBrief` 增加可选 `lifecycle_stage?`、`strength_score?`、`lifecycle_confidence?`。

- [ ] **Step 2: API** — `refreshShortTermSignals`、`fetchShortTermSectors`、`fetchThemeLifecycle(themeId, days=10)`；refresh timeout 与现一进二一致（偏长）。  

- [ ] **Step 3: Vitest 路径与参数**

```bash
cd frontend
pnpm exec vitest run src/api/short-term.test.ts
```

---

### Task 8: 看板短线雷达 UI + 紧凑题材卡

**Files:** `ShortTermRadarSection.tsx` 等、`ThemeDashboard.tsx`、`ThemeCard.tsx`、`ThemeRiseFallBar.tsx`、`ThemeLifecycleBadge.tsx`、测试

- [ ] **Step 1: `ThemeLifecycleBadge`** — 五阶段中文 + 色；未知不渲染  

- [ ] **Step 2: Radar 三面板** — Overview（展望/建议/结论/`degraded`）、Sectors（主线列表）、刷新按钮调 `signals/refresh`（未登录提示登录）  

- [ ] **Step 3: 挂到 `ThemeDashboard`** — 策略卡上方或紧邻；保留 `MarketStrategyCard` 与 `BoardUpgradeReference`  

- [ ] **Step 4: `ThemeCard`** — `p-3` 紧凑；展示徽章与强度分  

- [ ] **Step 5: `ThemeRiseFallBar`** — 高度略减（如 520→420）  

- [ ] **Step 6: 测试 + AppCardNav 可选链到 `/#short-term-radar`  

```bash
pnpm exec vitest run src/components/short-term src/components/ThemeCard.test.tsx src/features/dashboard/ThemeDashboard.test.tsx
```

---

### Task 9: 题材库阶段列 + 筛选

**Files:** `ThemeLibrary.tsx`、filters hook/类型、测试

- [ ] **Step 1: 表格列「阶段」「强度」** — null 显示 —  

- [ ] **Step 2: 筛选** — query 增加 `lifecycle_stage`（后端 list 支持同名 filter；若本迭代后端 filter 成本高，可先前端过滤当前页并在 UI 注明「当前页筛选」，但 **优先后端 filter**）  

- [ ] **Step 3: 测试筛选与列渲染  

```bash
pnpm exec vitest run src/features/themes/ThemeLibrary.test.tsx
```

---

### Task 10: 详情四维仪表 + 10 日轨迹

**Files:** `ThemeStrengthGauge.tsx`、`ThemeLifecycleTrend.tsx`、`ThemeDetail.tsx`、测试

- [ ] **Step 1: Gauge** — 四维条/雷达；`flow_score === null` 显示「回流暂缺」  

- [ ] **Step 2: Trend** — ECharts：强度折线 + 阶段色带；接 `fetchThemeLifecycle`  

- [ ] **Step 3: 接入详情页热度区旁；空态文案引导看板刷新  

- [ ] **Step 4: 测试  

```bash
pnpm exec vitest run src/features/themes/ThemeDetail.test.tsx src/components/ThemeStrengthGauge.test.tsx src/components/charts/ThemeLifecycleTrend.test.tsx
```

---

### Task 11: 端到端验收

- [ ] **Step 1: 后端**

```bash
cd backend
pytest tests/unit/test_short_term_models.py tests/unit/test_lifecycle_rules.py tests/unit/test_short_term_signal_repository.py tests/unit/test_short_term_signal_scraper.py tests/unit/test_sector_rotation_service.py tests/unit/test_short_term_service.py tests/unit/test_short_term_api.py tests/unit/test_short_term_rules.py -q
```

- [ ] **Step 2: 前端**

```bash
cd frontend
pnpm exec vitest run src/api/short-term.test.ts src/components/short-term src/components/ThemeLifecycleBadge.test.tsx src/components/ThemeStrengthGauge.test.tsx src/components/ThemeCard.test.tsx src/features/dashboard/ThemeDashboard.test.tsx src/features/themes/ThemeLibrary.test.tsx src/features/themes/ThemeDetail.test.tsx
```

- [ ] **Step 3: 对照 spec 验收表** — 五表、refresh partial、徽章/仪表/轨迹、兼容旧 overview/一进二字段、免责脚注  

- [ ] **Step 4:（可选）用户要求时再 git commit**，建议拆 commit：`feat(db): short-term radar tables` → `feat(short-term): ingest and lifecycle rules` → `feat(api): sectors and lifecycle` → `feat(ui): radar and gauges`

---

## Spec coverage checklist

| Spec 项 | Task |
|---------|------|
| 五表 + 生命周期列 | 1 |
| 幂等仓库 | 2 |
| 四维 + 五阶段规则 | 3 |
| 涨停/龙虎采集 | 4 |
| refresh 编排 + 读库 overview/candidates | 5 |
| `/signals/refresh` `/sectors` `/lifecycle` + theme join | 6 |
| 前端 API/类型 | 7 |
| 看板雷达 + 紧凑卡 | 8 |
| 题材库列+筛选 | 9 |
| 详情仪表+轨迹 | 10 |
| 降级/验收 | 5,6,11 |
| 不实现 P1–P5 挖掘/自选等 | （范围外） |

## 风险备注（执行时）

- 外网源不稳：必须以 `partial` + `missing_sources` 交付，禁止假回流。  
- `015` 须在 `014` 之后；若本地 revision 分叉先对齐 alembic heads。  
- 与旧 `2026-07-21` 计划字段冲突时，**以 `2026-07-25` spec 为准**（含 lifecycle 扩展列）。
