# Short-Term Opportunity Radar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full short-term opportunity radar data chain for sector rotation, risk signals, and yesterday-first-board to today-second-board stock selection, while making the dashboard Top 20 and theme cards more compact.

**Architecture:** Add a separate short-term signal domain alongside the existing theme/news domain. Backend tables store daily stock signals, dragon-tiger entries, sector snapshots, run state, and candidate outputs; services handle ingestion, rule scoring, and API aggregation; frontend displays a dense radar module plus compact theme rankings.

**Tech Stack:** Python FastAPI, SQLAlchemy async ORM, Alembic, MySQL 8.0, pytest, React, TanStack Query, Zustand-adjacent dashboard state, Vitest, ECharts, Tailwind.

---

## File Structure

- Create `backend/alembic/versions/012_create_short_term_signals.py`: MySQL tables and indexes for the short-term domain.
- Create `backend/app/models/short_term_signal.py`: ORM models for runs, daily signals, dragon-tiger entries, sector snapshots, and candidates.
- Modify `backend/app/models/__init__.py`: import the new models so Alembic metadata discovers them.
- Create `backend/app/schemas/short_term.py`: Pydantic request/response schemas.
- Create `backend/app/repositories/short_term.py`: query and idempotent write operations.
- Create `backend/app/services/short_term_rules.py`: deterministic rule engine.
- Create `backend/app/services/short_term.py`: orchestration and API aggregation service.
- Create `backend/app/scrapers/short_term.py`: short-term source parser and refresh entry point using injectable fixture-style providers first.
- Create `backend/app/api/short_term.py`: REST endpoints under `/short-term`.
- Modify `backend/app/main.py`: register the router and OpenAPI tag.
- Create backend tests under `backend/tests/unit/test_short_term_*.py`.
- Create `frontend/src/types/short-term.ts`: frontend API types.
- Create `frontend/src/api/short-term.ts` and `frontend/src/api/short-term.test.ts`: API client.
- Create `frontend/src/components/short-term/ShortTermRadarSection.tsx`.
- Create `frontend/src/components/short-term/ShortTermOverviewPanel.tsx`.
- Create `frontend/src/components/short-term/SectorRotationPanel.tsx`.
- Create `frontend/src/components/short-term/FirstToSecondCandidatesTable.tsx`.
- Create `frontend/src/components/short-term/ShortTermRuleBadges.tsx`.
- Create component tests beside each new component.
- Modify `frontend/src/features/dashboard/ThemeDashboard.tsx`: render the radar and compact layout.
- Modify `frontend/src/components/ThemeCard.tsx` and tests: compact card spacing.
- Modify `frontend/src/components/charts/ThemeRiseFallBar.tsx` and tests: compact Top 20 chart height.

## Task 1: Database Migration And ORM Models

**Files:**
- Create: `backend/alembic/versions/012_create_short_term_signals.py`
- Create: `backend/app/models/short_term_signal.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/unit/test_short_term_models.py`
- Test: `backend/tests/unit/test_mysql_migrations.py`

- [ ] **Step 1: Write failing model tests**

Add tests that import the ORM models and assert table names, critical columns, and index names.

```python
from app.models.short_term_signal import (
    DailyStockSignal,
    DragonTigerEntry,
    SectorRotationSnapshot,
    ShortTermCandidate,
    ShortTermSignalRun,
)


def test_short_term_models_define_expected_tables_and_indexes():
    assert DailyStockSignal.__tablename__ == "daily_stock_signals"
    assert DragonTigerEntry.__tablename__ == "dragon_tiger_entries"
    assert SectorRotationSnapshot.__tablename__ == "sector_rotation_snapshots"
    assert ShortTermSignalRun.__tablename__ == "short_term_signal_runs"
    assert ShortTermCandidate.__tablename__ == "short_term_candidates"

    daily_indexes = {index.name for index in DailyStockSignal.__table__.indexes}
    assert "idx_daily_stock_signals_date_type" in daily_indexes
    assert "idx_daily_stock_signals_date_stock" in daily_indexes
    assert "idx_daily_stock_signals_date_theme" in daily_indexes

    candidate_indexes = {index.name for index in ShortTermCandidate.__table__.indexes}
    assert "idx_short_term_candidates_date_strategy_rank" in candidate_indexes
```

- [ ] **Step 2: Run model tests and verify failure**

Run:

```bash
cd backend
pytest tests/unit/test_short_term_models.py -q
```

Expected: fail because `app.models.short_term_signal` does not exist.

- [ ] **Step 3: Implement ORM models**

Create models using `BigInteger` auto-increment PKs, `Date`, `DateTime(timezone=True)`, `Numeric`, `Boolean`, `JSON`, and FK links to `stocks.id` and `themes.id`. Use Chinese comments, English class and field names. Include all indexes from the spec.

- [ ] **Step 4: Add Alembic migration**

Create migration `012_create_short_term_signals.py` with `upgrade()` creating the five tables and `downgrade()` dropping them in reverse FK order. Use table and index names from the spec exactly.

- [ ] **Step 5: Register models**

Import the new classes in `backend/app/models/__init__.py` so metadata discovery includes them.

- [ ] **Step 6: Run migration and model tests**

Run:

```bash
cd backend
pytest tests/unit/test_short_term_models.py tests/unit/test_mysql_migrations.py -q
```

Expected: pass.

## Task 2: Backend Schemas And Repository

**Files:**
- Create: `backend/app/schemas/short_term.py`
- Create: `backend/app/repositories/short_term.py`
- Test: `backend/tests/unit/test_short_term_schemas.py`
- Test: `backend/tests/unit/test_short_term_repository.py`

- [ ] **Step 1: Write failing schema tests**

Add tests for JSON-friendly decimal serialization and degraded response fields.

```python
from datetime import date
from decimal import Decimal

from app.schemas.short_term import ShortTermCandidateItem, ShortTermOverviewResponse


def test_candidate_item_serializes_numeric_fields():
    item = ShortTermCandidateItem(
        stock_id=1,
        stock_code="000001",
        stock_name="平安银行",
        theme_id=2,
        theme_name="金融科技",
        score=Decimal("82.5"),
        rank=1,
        decision="candidate",
        price=Decimal("12.34"),
        float_market_cap=Decimal("6500000000"),
        market_cap=Decimal("12000000000"),
        matched_rules=["政策利好"],
        excluded_rules=[],
        risk_flags=[],
        outlook="情绪修复",
        operation_advice="只跟踪不追高",
        tracking_focus="开盘承接",
        core_conclusion="具备一进二观察价值",
    )

    payload = item.model_dump(mode="json")
    assert payload["score"] == 82.5
    assert payload["price"] == 12.34


def test_overview_response_exposes_degraded_state():
    response = ShortTermOverviewResponse(
        trade_date=date(2026, 7, 21),
        degraded=True,
        missing_sources=["dragon_tiger"],
        market_emotion="数据不完整",
        short_term_outlook="等待补全",
        operation_advice="降低仓位",
        tracking_focus=["一进二"],
        core_conclusion="龙虎榜缺失，结论降级",
        risk_signals=["龙虎榜缺失"],
        sector_count=0,
        candidate_count=0,
    )
    assert response.degraded is True
    assert response.missing_sources == ["dragon_tiger"]
```

- [ ] **Step 2: Run schema tests and verify failure**

Run:

```bash
cd backend
pytest tests/unit/test_short_term_schemas.py -q
```

Expected: fail because schema module does not exist.

- [ ] **Step 3: Implement schemas**

Create schemas for:

- `ShortTermRefreshResponse`
- `ShortTermOverviewResponse`
- `ShortTermCandidateItem`
- `ShortTermCandidateListResponse`
- `SectorRotationItem`
- `ShortTermSectorsResponse`

Use `field_serializer` for `Decimal | None` fields so the frontend receives numbers.

- [ ] **Step 4: Write failing repository tests**

Test idempotent candidate replacement by trade date and strategy, plus latest available trade date fallback.

- [ ] **Step 5: Implement repository**

Implement methods:

- `create_run(trade_date)`
- `finish_run(run_id, status, source_status, error_message=None)`
- `replace_daily_signals(trade_date, rows)`
- `replace_dragon_tiger_entries(trade_date, rows)`
- `replace_sector_snapshots(trade_date, rows)`
- `replace_candidates(trade_date, strategy, rows)`
- `list_candidates(trade_date, strategy)`
- `list_sector_snapshots(trade_date)`
- `get_latest_trade_date()`

- [ ] **Step 6: Run repository and schema tests**

Run:

```bash
cd backend
pytest tests/unit/test_short_term_schemas.py tests/unit/test_short_term_repository.py -q
```

Expected: pass.

## Task 3: Rule Engine

**Files:**
- Create: `backend/app/services/short_term_rules.py`
- Test: `backend/tests/unit/test_short_term_rules.py`

- [ ] **Step 1: Write failing rule tests**

Cover hard exclusions and scoring:

```python
from datetime import date, datetime
from decimal import Decimal

from app.services.short_term_rules import ShortTermRuleEngine


def make_signal(**overrides):
    base = {
        "trade_date": date(2026, 7, 20),
        "stock_id": 1,
        "stock_code": "000001",
        "stock_name": "测试股份",
        "theme_id": 10,
        "theme_name": "新题材",
        "signal_type": "first_limit_up",
        "first_limit_up_at": datetime(2026, 7, 20, 9, 35),
        "limit_up_order": 1,
        "is_one_word": False,
        "is_failed": False,
        "price": Decimal("12"),
        "float_market_cap": Decimal("5000000000"),
        "market_cap": Decimal("9000000000"),
        "amount": Decimal("800000000"),
        "turnover_rate": Decimal("12"),
        "catalysts": ["政策利好", "行业催化"],
        "theme_tags": ["主流题材", "新题材"],
        "dragon_tiger_net_amount": Decimal("10000000"),
        "risk_flags": [],
    }
    base.update(overrides)
    return base


def test_rule_engine_excludes_one_word_and_failed_limit_up():
    engine = ShortTermRuleEngine()
    results = engine.evaluate_first_to_second([
        make_signal(stock_id=1, is_one_word=True),
        make_signal(stock_id=2, is_failed=True),
    ])

    assert {item.stock_id for item in results if item.decision == "excluded"} == {1, 2}
    assert any("一字板" in rule for rule in results[0].excluded_rules)
    assert any("炸板" in rule for rule in results[1].excluded_rules)


def test_rule_engine_prefers_early_board_in_same_theme():
    engine = ShortTermRuleEngine()
    results = engine.evaluate_first_to_second([
        make_signal(stock_id=1, limit_up_order=2),
        make_signal(stock_id=2, limit_up_order=1),
    ])

    candidates = [item for item in results if item.decision == "candidate"]
    assert candidates[0].stock_id == 2
```

- [ ] **Step 2: Run rule tests and verify failure**

Run:

```bash
cd backend
pytest tests/unit/test_short_term_rules.py -q
```

Expected: fail because `ShortTermRuleEngine` does not exist.

- [ ] **Step 3: Implement rule dataclasses and engine**

Implement deterministic scoring:

- Base score: 50.
- Hard exclusion sets `decision="excluded"` and score no higher than 20.
- Add +10 policy benefit, +8 industry catalyst, +8 sudden event, +10 mainline theme, +8 new theme.
- Add +8 ideal float market cap `20-80亿`, +6 ideal total market cap `50-150亿`.
- Add +6 earlier same-theme board order compared with peers.
- Subtract -8 old/repeated theme, -8 no catalyst, -10 dragon-tiger net sell, -10 risk flags.
- Sort candidates by `decision`, score descending, then `limit_up_order` ascending.

- [ ] **Step 4: Run rule tests**

Run:

```bash
cd backend
pytest tests/unit/test_short_term_rules.py -q
```

Expected: pass.

## Task 4: Short-Term Scraper And Refresh Service

**Files:**
- Create: `backend/app/scrapers/short_term.py`
- Create: `backend/app/services/short_term.py`
- Test: `backend/tests/unit/test_short_term_scraper.py`
- Test: `backend/tests/unit/test_short_term_service.py`

- [ ] **Step 1: Write failing parser tests**

Use local fixture dictionaries, not live network, to parse daily signals and dragon-tiger entries.

```python
from app.scrapers.short_term import ShortTermSignalScraper


def test_parse_limit_pool_normalizes_first_board_signal():
    scraper = ShortTermSignalScraper()
    rows = scraper.parse_limit_pool([
        {
            "code": "000001",
            "name": "测试股份",
            "theme_name": "机器人",
            "signal_type": "first_limit_up",
            "first_limit_up_at": "09:35:00",
            "limit_up_order": 1,
            "is_one_word": False,
            "is_failed": False,
            "price": 12.3,
            "float_market_cap": 5000000000,
            "market_cap": 9000000000,
            "amount": 800000000,
            "turnover_rate": 12,
        }
    ])
    assert rows[0]["stock_code"] == "000001"
    assert rows[0]["signal_type"] == "first_limit_up"
    assert rows[0]["limit_up_order"] == 1
```

- [ ] **Step 2: Run parser tests and verify failure**

Run:

```bash
cd backend
pytest tests/unit/test_short_term_scraper.py -q
```

Expected: fail because scraper does not exist.

- [ ] **Step 3: Implement scraper parser and provider shell**

Create `ShortTermSignalScraper` with parse methods:

- `parse_limit_pool(raw_rows)`
- `parse_dragon_tiger(raw_rows)`
- `parse_sector_rows(raw_rows)`
- `run(trade_date)` returning parsed collections and source status.

Initial `run()` may use existing local provider hooks and should never fabricate missing fields; missing data is reflected in `source_status`.

- [ ] **Step 4: Write failing service tests**

Test that `refresh(trade_date)` creates a run, writes parsed rows, invokes the rule engine, stores candidates, and returns degraded state if dragon-tiger data is missing.

- [ ] **Step 5: Implement service orchestration**

`ShortTermService.refresh(trade_date)` should:

1. Create run.
2. Call scraper.
3. Replace daily signals, dragon-tiger entries, and sector snapshots for the trade date.
4. Build rule-engine inputs from repository rows.
5. Replace `first_to_second` candidates.
6. Finish run with `success`, `partial`, or `failed`.

- [ ] **Step 6: Run service tests**

Run:

```bash
cd backend
pytest tests/unit/test_short_term_scraper.py tests/unit/test_short_term_service.py -q
```

Expected: pass.

## Task 5: REST API

**Files:**
- Create: `backend/app/api/short_term.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/unit/test_short_term_api.py`

- [ ] **Step 1: Write failing API tests**

Use the app test client and mocked `ShortTermService` where existing tests use service mocks.

```python
async def test_short_term_overview_returns_degraded_state(async_client, monkeypatch):
    async def fake_overview(self, trade_date=None):
        return {
            "trade_date": "2026-07-21",
            "degraded": True,
            "missing_sources": ["dragon_tiger"],
            "market_emotion": "数据不完整",
            "short_term_outlook": "等待补全",
            "operation_advice": "降低仓位",
            "tracking_focus": ["一进二"],
            "core_conclusion": "龙虎榜缺失，结论降级",
            "risk_signals": ["龙虎榜缺失"],
            "sector_count": 0,
            "candidate_count": 0,
        }

    monkeypatch.setattr("app.services.short_term.ShortTermService.get_overview", fake_overview)
    response = await async_client.get("/api/v1/short-term/overview?trade_date=2026-07-21")
    assert response.status_code == 200
    assert response.json()["degraded"] is True
```

- [ ] **Step 2: Run API tests and verify failure**

Run:

```bash
cd backend
pytest tests/unit/test_short_term_api.py -q
```

Expected: fail because router is missing.

- [ ] **Step 3: Implement router and registration**

Add endpoints:

- `POST /api/v1/short-term/signals/refresh`
- `GET /api/v1/short-term/overview`
- `GET /api/v1/short-term/candidates`
- `GET /api/v1/short-term/sectors`

Register router in `create_app()` and add an OpenAPI tag named `short-term`.

- [ ] **Step 4: Run API tests**

Run:

```bash
cd backend
pytest tests/unit/test_short_term_api.py -q
```

Expected: pass.

## Task 6: Frontend Types And API Client

**Files:**
- Create: `frontend/src/types/short-term.ts`
- Create: `frontend/src/api/short-term.ts`
- Create: `frontend/src/api/short-term.test.ts`

- [ ] **Step 1: Write failing frontend API tests**

```typescript
import { describe, expect, it, vi } from 'vitest'
import { apiClient } from '@/api/client'
import { fetchShortTermOverview, refreshShortTermSignals } from './short-term'

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('short-term api', () => {
  it('fetches overview with trade date', async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        trade_date: '2026-07-21',
        degraded: true,
        missing_sources: ['dragon_tiger'],
        market_emotion: '数据不完整',
        short_term_outlook: '等待补全',
        operation_advice: '降低仓位',
        tracking_focus: ['一进二'],
        core_conclusion: '龙虎榜缺失，结论降级',
        risk_signals: ['龙虎榜缺失'],
        sector_count: 0,
        candidate_count: 0,
      },
    })

    const result = await fetchShortTermOverview('2026-07-21')

    expect(apiClient.get).toHaveBeenCalledWith('/short-term/overview', {
      params: { trade_date: '2026-07-21' },
    })
    expect(result.degraded).toBe(true)
  })

  it('posts refresh with extended timeout', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { generated_candidates: 2 } })
    await refreshShortTermSignals('2026-07-21')
    expect(apiClient.post).toHaveBeenCalledWith(
      '/short-term/signals/refresh',
      undefined,
      { params: { trade_date: '2026-07-21' }, timeout: 300_000 }
    )
  })
})
```

- [ ] **Step 2: Run frontend API tests and verify failure**

Run:

```bash
cd frontend
pnpm exec vitest run src/api/short-term.test.ts
```

Expected: fail because module does not exist.

- [ ] **Step 3: Implement types and API client**

Types should mirror backend schemas and use numbers for decimal JSON fields. API client functions:

- `fetchShortTermOverview(tradeDate?: string)`
- `fetchShortTermCandidates(tradeDate?: string, strategy = 'first_to_second')`
- `fetchShortTermSectors(tradeDate?: string)`
- `refreshShortTermSignals(tradeDate?: string)`

- [ ] **Step 4: Run frontend API tests**

Run:

```bash
cd frontend
pnpm exec vitest run src/api/short-term.test.ts
```

Expected: pass.

## Task 7: Frontend Radar Components

**Files:**
- Create: `frontend/src/components/short-term/ShortTermRadarSection.tsx`
- Create: `frontend/src/components/short-term/ShortTermOverviewPanel.tsx`
- Create: `frontend/src/components/short-term/SectorRotationPanel.tsx`
- Create: `frontend/src/components/short-term/FirstToSecondCandidatesTable.tsx`
- Create: `frontend/src/components/short-term/ShortTermRuleBadges.tsx`
- Create tests beside each component.

- [ ] **Step 1: Write failing component tests**

Focus on visible behavior:

```typescript
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ShortTermOverviewPanel } from './ShortTermOverviewPanel'

describe('ShortTermOverviewPanel', () => {
  it('shows degraded source warning and core conclusion', () => {
    render(
      <ShortTermOverviewPanel
        overview={{
          trade_date: '2026-07-21',
          degraded: true,
          missing_sources: ['dragon_tiger'],
          market_emotion: '数据不完整',
          short_term_outlook: '等待补全',
          operation_advice: '降低仓位',
          tracking_focus: ['一进二'],
          core_conclusion: '龙虎榜缺失，结论降级',
          risk_signals: ['龙虎榜缺失'],
          sector_count: 0,
          candidate_count: 0,
        }}
      />
    )

    expect(screen.getByText('短线机会雷达')).toBeInTheDocument()
    expect(screen.getByText(/数据不完整/)).toBeInTheDocument()
    expect(screen.getByText('龙虎榜缺失，结论降级')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run component tests and verify failure**

Run:

```bash
cd frontend
pnpm exec vitest run src/components/short-term
```

Expected: fail because components do not exist.

- [ ] **Step 3: Implement components**

Use dense operational layout:

- No landing-page treatment.
- No nested cards.
- Cards only for repeated candidate rows or compact panels.
- Show degraded status clearly.
- Show matched rules, excluded rules, and risk flags as compact badges.
- Candidate table columns: rank, stock, theme, score, price, float market cap, matched rules, risk flags, advice.

- [ ] **Step 4: Run component tests**

Run:

```bash
cd frontend
pnpm exec vitest run src/components/short-term
```

Expected: pass.

## Task 8: Dashboard Integration And Compact Existing UI

**Files:**
- Modify: `frontend/src/features/dashboard/ThemeDashboard.tsx`
- Modify: `frontend/src/components/ThemeCard.tsx`
- Modify: `frontend/src/components/ThemeCard.test.tsx`
- Modify: `frontend/src/components/charts/ThemeRiseFallBar.tsx`
- Modify: `frontend/src/components/charts/ThemeRiseFallBar.test.tsx`
- Test: `frontend/src/features/dashboard/ThemeDashboard.test.tsx`

- [ ] **Step 1: Write failing dashboard and compact UI tests**

Add assertions:

- Dashboard renders `短线机会雷达`.
- Hot theme grid uses denser 2xl/3xl classes if present in local Tailwind config.
- `ThemeCard` uses compact padding.
- `ThemeRiseFallBar` default height is smaller than 520px.

```typescript
it('renders short-term radar before hot theme cards', async () => {
  renderThemeDashboard()
  const radar = await screen.findByText('短线机会雷达')
  const hotThemes = screen.getByText(/热门题材 Top/)
  expect(radar.compareDocumentPosition(hotThemes) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
})
```

- [ ] **Step 2: Run targeted frontend tests and verify failure**

Run:

```bash
cd frontend
pnpm exec vitest run src/features/dashboard/ThemeDashboard.test.tsx src/components/ThemeCard.test.tsx src/components/charts/ThemeRiseFallBar.test.tsx
```

Expected: fail because dashboard integration and compact classes are not implemented.

- [ ] **Step 3: Integrate radar**

In `ThemeDashboard.tsx`, add queries for overview, sectors, and candidates. Render `ShortTermRadarSection` above the ranking grid or immediately before hot themes. Add refresh handler that calls `refreshShortTermSignals()` and refetches radar queries.

- [ ] **Step 4: Compact Top 20 chart**

In `ThemeRiseFallBar.tsx`, reduce default height from `520px` to `360px`, reduce label font size if needed, and make empty chart height match.

- [ ] **Step 5: Compact theme cards**

In `ThemeCard.tsx`, reduce padding from `p-4` to `p-3`, reduce vertical gaps, keep keyboard focus and hover affordance intact.

- [ ] **Step 6: Run frontend tests and lint**

Run:

```bash
cd frontend
pnpm exec vitest run src/api/short-term.test.ts src/components/short-term src/features/dashboard/ThemeDashboard.test.tsx src/components/ThemeCard.test.tsx src/components/charts/ThemeRiseFallBar.test.tsx
pnpm exec eslint src/api/short-term.ts src/components/short-term src/features/dashboard/ThemeDashboard.tsx src/components/ThemeCard.tsx src/components/charts/ThemeRiseFallBar.tsx
```

Expected: pass.

## Task 9: End-To-End Verification

**Files:**
- Modify if needed: docs or tests surfaced by verification.

- [ ] **Step 1: Run backend targeted tests**

Run:

```bash
cd backend
pytest tests/unit/test_short_term_models.py tests/unit/test_short_term_schemas.py tests/unit/test_short_term_repository.py tests/unit/test_short_term_rules.py tests/unit/test_short_term_scraper.py tests/unit/test_short_term_service.py tests/unit/test_short_term_api.py -q
```

Expected: pass.

- [ ] **Step 2: Run frontend targeted tests**

Run:

```bash
cd frontend
pnpm exec vitest run src/api/short-term.test.ts src/components/short-term src/features/dashboard/ThemeDashboard.test.tsx src/components/ThemeCard.test.tsx src/components/charts/ThemeRiseFallBar.test.tsx
```

Expected: pass.

- [ ] **Step 3: Run formatting and lint**

Run:

```bash
cd backend
ruff check app tests
black --check app tests
cd ../frontend
pnpm exec eslint src --ext ts,tsx --report-unused-disable-directives --max-warnings 0
pnpm exec prettier --check src
```

Expected: pass. If existing unrelated files fail, record the exact unrelated failures and keep this feature's touched files clean.

- [ ] **Step 4: Manual API smoke test**

Start the backend and run:

```bash
curl "http://localhost:8000/api/v1/short-term/overview"
curl "http://localhost:8000/api/v1/short-term/candidates?strategy=first_to_second"
```

Expected: JSON responses with `degraded` and `missing_sources` fields present.

- [ ] **Step 5: Manual UI smoke test**

Start the frontend and verify:

- Dashboard shows “短线机会雷达”.
- Degraded state is visible when short-term sources are incomplete.
- Hot theme Top 20 chart is visibly shorter.
- Theme cards are more compact and still clickable.

## Self-Review

- Spec coverage: the plan covers data model, scraper, rules, API, frontend radar, compact Top 20/chart/cards, tests, and degraded states.
- Completion scan: every task names files, commands, expected results, and concrete behaviors.
- Type consistency: backend response names map to frontend `short-term.ts`; strategy value is consistently `first_to_second`; degraded state consistently uses `degraded` and `missing_sources`.
