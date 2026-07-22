# First To Second Live Candidates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将“一进二打板参考”从静态规则卡改为可自动刷新、可解释的一进二候选股票列表。

**Architecture:** 后端新增短线候选响应类型、实时刷新 API 和可注入的 AKShare 候选采集服务；规则引擎只做可验证硬筛和加分，模型/新闻催化缺失时降级但不伪造。前端复用现有看板 React Query 风格，卡片内展示候选、排除原因、刷新状态和降级提示。

**Tech Stack:** FastAPI, SQLAlchemy async session, AKShare, React, TanStack Query, Vitest, Pytest.

---

### Task 1: Backend Candidate API

**Files:**
- Modify: `backend/app/schemas/short_term.py`
- Modify: `backend/app/services/short_term.py`
- Modify: `backend/app/api/short_term.py`
- Test: `backend/tests/unit/test_short_term_schemas.py`
- Test: `backend/tests/unit/test_short_term_api.py`

- [ ] Add `FirstToSecondCandidateItem`, `FirstToSecondCandidateResponse`, and refresh run response schemas.
- [ ] Add `GET /short-term/first-to-second` and `POST /short-term/first-to-second/refresh`.
- [ ] Tests assert response includes real stock fields, matched/excluded rules, degraded status, and API calls service with `force_refresh`.

### Task 2: Live Candidate Service

**Files:**
- Create: `backend/app/services/first_to_second.py`
- Test: `backend/tests/unit/test_first_to_second_service.py`

- [ ] Add an injectable provider that fetches yesterday first-limit-up pool and today limit-up/near-limit-up compatible rows.
- [ ] Normalize AKShare column variants for code, name, price, first board time, open board count, streak days, market cap, float market cap, amount, turnover, and one-word flag.
- [ ] Apply hard rules: price > 25, float cap < 10 or > 100, failed/one-word first board, poor liquidity.
- [ ] Score candidates with policy/industry/event catalysts from available theme/news text when present; missing model is a degradation note, not fake data.
- [ ] Sort same-theme candidates by first board time.

### Task 3: Frontend Realtime Card

**Files:**
- Modify: `frontend/src/types/short-term.ts`
- Modify: `frontend/src/api/short-term.ts`
- Modify: `frontend/src/components/BoardUpgradeReference.tsx`
- Test: `frontend/src/components/BoardUpgradeReference.test.tsx`
- Test: `frontend/src/api/short-term.test.ts`

- [ ] Add API client functions for fetch and refresh.
- [ ] Replace static rule list with candidate table/list, status row, refresh button, degraded/missing-source hints, and compact rule badges.
- [ ] Tests assert rendered stock rows, refresh click callback, empty state, and degraded state.

### Task 4: Dashboard Wiring

**Files:**
- Modify: `frontend/src/features/dashboard/ThemeDashboard.tsx`
- Test: `frontend/src/features/dashboard/ThemeDashboard.test.tsx`

- [ ] Add React Query for first-to-second candidates.
- [ ] Wire card refresh to `POST /refresh` then refetch candidates.
- [ ] Include candidate refresh in dashboard refresh and auto refresh.
- [ ] Verify with backend pytest, frontend vitest, ESLint, and Vite build.
