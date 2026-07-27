# 看板刷新集中化与多源竞速 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 顶部仅保留可取消的轻量/全量刷新；分板块原子更新与时间戳；轻量与全量多源竞速且仅胜出源落正式库；实时资讯隔离。

**Architecture:** 前端用 `AbortController` + 分板块 `setQueryData` 编排；后端将「采集到内存草稿」与「写入正式库」拆开，竞速取先完成的完整草稿再单路 commit。全量进度通过 race 状态轮询驱动进度条。

**Tech Stack:** FastAPI, asyncio, SQLAlchemy, React, TanStack Query, axios AbortSignal, Vitest, Pytest

**Spec:** `docs/superpowers/specs/2026-07-27-dashboard-refresh-centralize-design.md`

**Prerequisite:** 落地并保留「全量不挡轻量」解耦锁改动（`quotes_refresh_lock`、启动僵尸清理、前端 409 文案）；若尚未提交，先作为 Task 0 提交。

**Phasing:** Phase A 可先上线（集中刷新+取消+分栏时间，全量暂仍串行/现有 fallback）；Phase B 再上多源竞速落库。两阶段各自可测、可提交。

---

## File map

| File | Responsibility |
|---|---|
| `frontend/src/components/DashboardRefreshControls.tsx` | 替换 AutoRefreshButton：轻量/全量/取消，无自动刷新、无源下拉 |
| `frontend/src/features/dashboard/sectionRefresh.ts` | 板块 id、本地刷新时间读写、原子 commit 辅助 |
| `frontend/src/features/dashboard/ThemeDashboard.tsx` | 编排轻量/全量/取消；去掉 useAutoRefresh 与板块内刷新 |
| `frontend/src/components/short-term/ShortTermRadarSection.tsx` | 移除「刷新信号」；展示 `refreshedAt` |
| `frontend/src/components/BoardUpgradeReference.tsx` | 移除「实时刷新」；展示 `refreshedAt` |
| `frontend/src/api/scraper.ts` | AbortSignal；`runScraperRace` / cancel / poll |
| `frontend/src/api/client.ts` | 确保 POST/GET 透传 `signal` |
| `backend/app/scrapers/draft_race.py` | 通用多源竞速：并行 collect，胜出 commit，cancel |
| `backend/app/scrapers/eastmoney.py` | `collect_theme_quotes` / `collect_full`（不写库） |
| `backend/app/scrapers/akshare.py` | 同上（能力范围内） |
| `backend/app/api/scraper.py` | `run-race`、race 进度、cancel；refresh-quotes 竞速 |
| `backend/app/services/strategy_quote_refresh.py` | 串行 fallback → 并行竞速后再落库 |
| `docs/superpowers/specs/2026-07-27-refresh-quotes-decouple-design.md` | 保持有效；本 plan 叠加其上 |

---

## Phase A — 前端集中刷新、取消、分栏时间

### Task 1: 板块刷新时间工具

**Files:**
- Create: `frontend/src/features/dashboard/sectionRefresh.ts`
- Create: `frontend/src/features/dashboard/sectionRefresh.test.ts`

- [ ] **Step 1: Write failing tests**

```ts
import { describe, expect, it, beforeEach } from 'vitest'
import {
  SECTION_IDS,
  readSectionRefreshedAt,
  writeSectionRefreshedAt,
  formatSectionRefreshedAt,
} from './sectionRefresh'

describe('sectionRefresh', () => {
  beforeEach(() => localStorage.clear())

  it('persists and formats section timestamps', () => {
    const at = '2026-07-27T02:32:15.000Z'
    writeSectionRefreshedAt(SECTION_IDS.heatRanking, at)
    expect(readSectionRefreshedAt(SECTION_IDS.heatRanking)).toBe(at)
    expect(formatSectionRefreshedAt(at)).toMatch(/\d{2}:\d{2}:\d{2}/)
  })

  it('returns null when missing', () => {
    expect(readSectionRefreshedAt(SECTION_IDS.riseRanking)).toBeNull()
    expect(formatSectionRefreshedAt(null)).toBe('暂无')
  })
})
```

- [ ] **Step 2: Run test — expect FAIL (module missing)**

Run: `cd frontend && pnpm exec vitest run src/features/dashboard/sectionRefresh.test.ts`

- [ ] **Step 3: Implement**

```ts
export const SECTION_IDS = {
  heatRanking: 'heat-ranking',
  riseRanking: 'rise-ranking',
  strategyCard: 'strategy-card',
  shortTermRadar: 'short-term-radar',
  firstToSecond: 'first-to-second',
  marketSignals: 'market-signals',
  indicatorSignals: 'indicator-signals',
} as const

export type SectionId = (typeof SECTION_IDS)[keyof typeof SECTION_IDS]

const STORAGE_PREFIX = 'dashboard-section-refreshed-at:'

export function readSectionRefreshedAt(id: SectionId): string | null {
  try {
    return localStorage.getItem(STORAGE_PREFIX + id)
  } catch {
    return null
  }
}

export function writeSectionRefreshedAt(id: SectionId, iso: string): void {
  try {
    localStorage.setItem(STORAGE_PREFIX + id, iso)
  } catch {
    /* ignore quota */
  }
}

export function formatSectionRefreshedAt(iso: string | null): string {
  if (!iso) return '暂无'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '暂无'
  return d.toLocaleTimeString('zh-CN', { hour12: false })
}
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/dashboard/sectionRefresh.ts frontend/src/features/dashboard/sectionRefresh.test.ts
git commit -m "feat: 看板分板块刷新时间存储"
```

---

### Task 2: DashboardRefreshControls（无自动刷新）

**Files:**
- Create: `frontend/src/components/DashboardRefreshControls.tsx`
- Create: `frontend/src/components/DashboardRefreshControls.test.tsx`
- Modify later: retire auto-refresh usage in ThemeDashboard（本任务只新建控件）

- [ ] **Step 1: Write failing UI test**

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { DashboardRefreshControls } from './DashboardRefreshControls'

describe('DashboardRefreshControls', () => {
  it('shows light/full and cancel when busy', () => {
    const onCancel = vi.fn()
    render(
      <DashboardRefreshControls
        isRefreshing
        isUpdating={false}
        onRefresh={vi.fn()}
        onFullUpdate={vi.fn()}
        onCancel={onCancel}
        refreshElapsedLabel="0:12"
      />
    )
    expect(screen.getByRole('button', { name: /取消/ })).toBeInTheDocument()
    expect(screen.queryByText('自动刷新')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /取消/ }))
    expect(onCancel).toHaveBeenCalled()
  })

  it('hides cancel when idle', () => {
    render(
      <DashboardRefreshControls
        isRefreshing={false}
        isUpdating={false}
        onRefresh={vi.fn()}
        onFullUpdate={vi.fn()}
        onCancel={vi.fn()}
      />
    )
    expect(screen.queryByRole('button', { name: /取消/ })).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Implement component** — 按钮：刷新 / 全量更新 /（busy 时）取消；无源下拉、无自动刷新；busy 时轻量与全量 disable，取消可用。

- [ ] **Step 3: Tests PASS**

- [ ] **Step 4: Commit** `feat: 顶部轻量全量取消刷新控件`

---

### Task 3: API 透传 AbortSignal

**Files:**
- Modify: `frontend/src/api/scraper.ts`
- Modify: `frontend/src/api/short-term.ts`（refresh 相关函数加可选 `signal?: AbortSignal`）
- Modify: `frontend/src/api/themes.ts` 或实际 ranking fetch 模块（同样加 signal）
- Test: `frontend/src/api/scraper.test.ts`

- [ ] **Step 1: Extend clients**

```ts
export async function refreshThemeQuotes(
  signal?: AbortSignal
): Promise<ThemeQuotesRefreshResult> {
  const { data } = await apiClient.post<ThemeQuotesRefreshResult>(
    '/scraper/refresh-quotes',
    null,
    { timeout: 120_000, signal }
  )
  return data
}
```

对 `refreshShortTermData`、`refreshShortTermSignals`、`refreshFirstToSecondCandidates`、`fetchThemeRanking`、`fetchThemes`（涨幅榜）、`fetchMarketSignals`、`fetchIndicatorSignals`、`fetchShortTermSectors`、`fetchFirstToSecondCandidates` 同样增加可选 `signal` 并传入 axios config。

- [ ] **Step 2: Test that options include signal**（mock axios 断言 `config.signal`）

- [ ] **Step 3: Commit** `feat: 看板刷新 API 支持 AbortSignal`

---

### Task 4: 移除板块内刷新按钮 + 展示分栏时间

**Files:**
- Modify: `frontend/src/components/short-term/ShortTermRadarSection.tsx`
- Modify: `frontend/src/components/BoardUpgradeReference.tsx`
- Modify: 热度榜/涨幅榜标题组件（ThemeDashboard 内或子组件）
- Modify: `frontend/src/components/short-term/MarketStrategyCard.tsx`（若有标题区）
- Test: 对应 `*.test.tsx`

- [ ] **Step 1:** 删除「刷新信号」按钮与 `handleRefresh`；props 增加 `refreshedAtLabel: string`、`isSectionRefreshing?: boolean`；空态文案改为「请使用顶部刷新」。

- [ ] **Step 2:** `BoardUpgradeReference` 删除 `onRefresh` / 「实时刷新」；增加 `refreshedAtLabel`。

- [ ] **Step 3:** 各板块标题旁渲染 `刷新于 {refreshedAtLabel}`。

- [ ] **Step 4:** 更新测试（不再期望刷新按钮；期望时间文案）。

- [ ] **Step 5: Commit** `feat: 板块刷新入口上收并展示分栏时间`

---

### Task 5: ThemeDashboard 编排（原子更新 + 取消）

**Files:**
- Modify: `frontend/src/features/dashboard/ThemeDashboard.tsx`
- Modify: `frontend/src/features/dashboard/ThemeDashboard.test.tsx`
- Modify: `frontend/src/components/GlobalKeyboardShortcuts.tsx`（R 仍触发轻量；busy 时可映射取消可选，默认仍刷新）

**核心逻辑（写入实现时保持此语义）：**

```ts
type RefreshSession = {
  controller: AbortController
  mode: 'light' | 'full'
}

const sessionRef = useRef<RefreshSession | null>(null)

async function commitSection<T>(
  sectionId: SectionId,
  queryKey: unknown[],
  fetcher: (signal: AbortSignal) => Promise<T>,
  signal: AbortSignal
): Promise<boolean> {
  try {
    const data = await fetcher(signal)
    if (signal.aborted) return false
    queryClient.setQueryData(queryKey, data)
    const iso = new Date().toISOString()
    writeSectionRefreshedAt(sectionId, iso)
    setSectionTimes((prev) => ({ ...prev, [sectionId]: iso }))
    return true
  } catch (e) {
    if (isAbortError(e) || signal.aborted) return false
    throw e
  }
}

function cancelRefresh() {
  sessionRef.current?.controller.abort()
  sessionRef.current = null
  setIsDashboardRefreshing(false)
  setIsUpdating(false)
  setUpdateResult({ type: 'info', message: '已取消，已保留成功板块' })
}
```

**轻量流水线顺序：**

1. `refreshThemeQuotes(signal)` — 失败则整次轻量行情步骤失败（已成功板块保留）
2. 并行/分步：`commitSection` 热度榜、涨幅榜、market-signals、indicator-signals
3. 若周期就绪：`refreshShortTermData` + commit 策略 overview
4. 若已登录：`refreshShortTermSignals` + commit sectors
5. `refreshFirstToSecondCandidates` + commit candidates
6. **永不**调用 news refresh

**全量（Phase A）：** 仍调用现有 `runScraperWithFallback`，轮询时检查 `signal.aborted`；abort 后停止轮询等待（后台任务可能仍跑——Phase B 用 race cancel 真正停）。落库 wait 结束后再跑与轻量相同的分板块 commit。进度条继续用现有 `updateResult` + LoadingBar。

**移除：** `useAutoRefresh`、silent 自动刷新、`selectedScraperSource` 下拉、`handleFirstToSecondRefresh` 按钮接线、AutoRefreshButton。

- [ ] **Step 1: 改测试** — 无自动刷新；轻量会调 signals + first-to-second refresh；取消后 mock abort 不覆盖 setQueryData；资讯 mock 不被调用。

- [ ] **Step 2: 实现编排**

- [ ] **Step 3: `pnpm exec vitest run src/features/dashboard` PASS**

- [ ] **Step 4: Commit** `feat: 看板轻量全量可取消分板块刷新`

---

### Task 6: Phase A 收尾

- [ ] 删除或停用 `frontend/src/hooks/useAutoRefresh.ts` 仅当无其它引用；若 AccountSettings 等仍用则保留 hook、仅看板不用。
- [ ] 手动点检：轻量中点取消 → 已出结果的板块时间更新，未完成保持旧数据。
- [ ] Commit 任何遗漏：`chore: 移除看板自动刷新入口`

---

## Phase B — 多源竞速（仅胜出落库）

### Task 7: 草稿采集 API（东财行情）

**Files:**
- Modify: `backend/app/scrapers/eastmoney.py`
- Test: `backend/tests/unit/test_eastmoney_quotes_draft.py`（新建）

- [ ] **Step 1: Failing test** — `collect_theme_quotes` 返回 `(trade_date, themes)` 且 **不**调用 `_save_themes`（mock spy）。

- [ ] **Step 2: Implement**

```python
async def collect_theme_quotes(
    self, *, only_codes: set[str] | None = None
) -> tuple[date | None, list[dict[str, Any]]]:
    # 现 refresh_theme_quotes 的 fetch/parse 部分，去掉 await self._save_themes
    ...
    return trade_date, themes

async def refresh_theme_quotes(...):
    trade_date, themes = await self.collect_theme_quotes(only_codes=only_codes)
    if not themes:
        return None, 0
    await self._save_themes(themes)
    return trade_date, len(themes)
```

- [ ] **Step 3: Tests PASS + Commit** `refactor: 东财题材行情支持仅采集不落库`

---

### Task 8: 轻量行情多源竞速服务

**Files:**
- Create: `backend/app/services/quotes_refresh_race.py`
- Modify: `backend/app/api/scraper.py`（`refresh_theme_quotes` 改调 race）
- Modify: `backend/app/services/strategy_quote_refresh.py`（并行竞速）
- Test: `backend/tests/unit/test_quotes_refresh_race.py`

- [ ] **Step 1: Failing tests**

```python
@pytest.mark.asyncio
async def test_race_commits_only_winner(monkeypatch):
    saves = []

    async def slow_collect():
        await asyncio.sleep(0.05)
        return date.today(), [{"code": "BK0001", "name": "慢"}]

    async def fast_collect():
        return date.today(), [{"code": "BK0002", "name": "快"}]

    async def save(themes):
        saves.append(themes)

    result = await race_theme_quotes(
        collectors=[("slow", slow_collect), ("fast", fast_collect)],
        save=save,
    )
    assert result.source == "fast"
    assert saves == [[{"code": "BK0002", "name": "快"}]]
```

```python
@pytest.mark.asyncio
async def test_race_cancel_before_save():
    cancelled = asyncio.Event()
    ...
    # cancel mid-flight → save not called
```

- [ ] **Step 2: Implement `race_theme_quotes`** — `asyncio.wait(..., FIRST_COMPLETED)`；校验胜出 `len(themes) >= MIN`；cancel 其余 task；再 `await save(winner_themes)`。

- [ ] **Step 3: Wire `POST /refresh-quotes`** 使用 eastmoney + akshare（akshare 用现有 strategy 路径的板块列表能力；若全量题材列表 akshare 不稳定，至少两源：eastmoney 主 + akshare 子集，文档注明）。

- [ ] **Step 4: strategy_quote_refresh 改为并行 race 再单次 `_save_themes`**，删除「先东财写库再失败」路径。

- [ ] **Step 5: Commit** `feat: 轻量行情多源竞速仅胜出落库`

---

### Task 9: 全量 collect / commit 拆分

**Files:**
- Modify: `backend/app/scrapers/eastmoney.py` — `collect_full()` 返回内存结构，不写 DB
- Modify: `backend/app/scrapers/akshare.py` — 同接口（返回可 commit 的草稿）
- Create: `backend/app/scrapers/draft_types.py` — `FullScrapeDraft(themes, stocks_by_theme_code, trade_date, source)`
- Test: unit tests with mocked HTTP

**约定：**

```python
@dataclass
class FullScrapeDraft:
    source: str
    trade_date: date | None
    themes: list[dict[str, Any]]
    stocks_by_code: dict[str, list[dict[str, Any]]]  # theme code -> stocks

async def collect_full(self, cancel: asyncio.Event) -> FullScrapeDraft:
    ...
    # 循环拉成分股时 if cancel.is_set(): raise asyncio.CancelledError

async def commit_full(self, draft: FullScrapeDraft) -> int:
    await self._save_themes(draft.themes)
    total = 0
    for code, stocks in draft.stocks_by_code.items():
        total += await self._save_theme_stocks(...)  # 复用现有保存
    return len(draft.themes) + total
```

- [ ] **Step 1–4:** TDD 拆分 eastmoney；akshare 能提供的最大集合（若无成分股则 themes-only draft，完成条件写清：themes 非空即视为可胜出）。

- [ ] **Step 5: Commit** `refactor: 全量爬虫采集与落库拆分`

---

### Task 10: Scraper race 调度 API

**Files:**
- Create: `backend/app/scrapers/full_race.py`
- Modify: `backend/app/scrapers/scheduler.py` — 注册 race 状态
- Modify: `backend/app/api/scraper.py`
- Modify: `backend/app/schemas/scraper.py`
- Test: `backend/tests/unit/test_full_race.py`, `backend/tests/integration/test_scraper_api.py`

**API：**

- `POST /api/v1/scraper/run-race` → `{ race_id, status: "racing", sources: [...] }`
- `GET /api/v1/scraper/race/{race_id}` → `{ status, phase, progress_pct, sources: [{id, progress_pct, status}], winner, error }`
- `POST /api/v1/scraper/race/{race_id}/cancel`

**行为：** 并行 `collect_full`；`FIRST_COMPLETED` 且 draft 有效 → 设 winner → `phase=committing` → `commit_full` → `completed`；其余 cancel；进度 `progress_pct = max(source progresses)`，commit 阶段映射 70–90。

- [ ] Tests: winner-only commit；cancel 不 commit；双失败 → failed

- [ ] Commit `feat: 全量多源竞速 API`

---

### Task 11: 前端接入 run-race + 进度

**Files:**
- Modify: `frontend/src/api/scraper.ts` — `startScraperRace`, `fetchScraperRace`, `cancelScraperRace`
- Modify: `ThemeDashboard.tsx` — 全量改 race；取消调 `cancelScraperRace` + abort 局部分板块
- Modify: 进度条文案按 `phase` / `progress_pct`
- Test: scraper + ThemeDashboard tests

- [ ] 删除对 `runScraperWithFallback` 的看板依赖（可保留函数供其它用途或标 deprecated）

- [ ] Commit `feat: 看板全量更新改多源竞速`

---

### Task 12: 端到端验收与文档

- [ ] 对照 spec 验收清单逐条勾选
- [ ] 更新 `docs/superpowers/specs/2026-07-27-dashboard-refresh-centralize-design.md` 状态为「已实现」或附实现日期
- [ ] 全量进行中点轻量仍可用（解耦锁回归）
- [ ] Commit `docs: 看板刷新集中化验收说明`

---

## Spec coverage check

| Spec 项 | Task |
|---|---|
| 顶部仅轻量/全量/取消，无自动刷新/无源下拉 | 2, 5, 6 |
| 移除雷达/一进二刷新按钮 | 4 |
| 除资讯外都刷；资讯隔离 | 5 |
| 取消保留成功板块 | 5 |
| 分栏细粒度时间 | 1, 4, 5 |
| 全量进度条 | 5 (A), 11 (B) |
| 轻量多源竞速仅胜出落库 | 7, 8 |
| 全量多源竞速仅胜出落库 | 9, 10, 11 |
| 全量不挡轻量 | Prerequisite + 回归 Task 12 |

## Placeholder / consistency review

- SectionId 与 `SECTION_IDS` 在 Task 1 定义，Task 4–5 复用同一常量。
- Race API 路径统一 `/scraper/run-race`、`/scraper/race/{id}`、`/scraper/race/{id}/cancel`。
- Phase A 全量 abort 仅停前端等待；真正取消采集在 Phase B Task 10–11。
