# Market Signal Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将市场行为板块从实际题材的列表、排行、搜索、分类、导出和统计中排除，并在仪表盘独立展示。

**Architecture:** 后端以集中代码集合和 SQLAlchemy 条件作为唯一分类来源，普通题材仓储查询统一排除，独立仓储方法只返回市场表现。前端通过独立查询加载市场表现，同时用普通题材分页响应的 `total` 作为真实题材总数，并复用现有详情导航和更新反馈。

**Tech Stack:** FastAPI、SQLAlchemy Async、Pydantic、pytest、React、TypeScript、TanStack Query、Vitest、Testing Library、Tailwind CSS

---

## 文件结构

- 新建 `backend/app/domain/theme_classification.py`：市场表现代码集合、纯判断函数和 SQLAlchemy 包含/排除条件。
- 修改 `backend/app/repositories/theme.py`：所有普通题材查询应用排除条件，增加市场表现查询。
- 修改 `backend/app/services/theme.py`：将市场表现实体转换为现有排行响应。
- 修改 `backend/app/api/theme.py`：在动态详情路由前注册 `/market-signals`。
- 修改 `frontend/src/api/theme.ts`：增加市场表现请求函数。
- 新建 `frontend/src/components/MarketSignalSection.tsx`：独立区域及加载、空、错误状态。
- 修改 `frontend/src/features/dashboard/ThemeDashboard.tsx`：并行加载总数和市场表现，更新后一起刷新。
- 修改对应后端和前端测试文件：覆盖分类、SQL 条件、接口契约、统计口径、展示和刷新。

### Task 1: 集中分类规则

**Files:**
- Create: `backend/app/domain/theme_classification.py`
- Create: `backend/tests/unit/test_theme_classification.py`

- [ ] **Step 1: 写失败测试**

测试 `BK0815`、`BK0816`、`BK1631`、`BK1638`、`BK1715` 等已确认代码返回 `True`，普通概念代码返回 `False`；编译 SQLAlchemy 条件后分别包含 `NOT IN` 和 `IN`。

- [ ] **Step 2: 验证测试因模块不存在而失败**

Run: `cd backend; python -m pytest tests/unit/test_theme_classification.py -q`

Expected: FAIL，提示 `app.domain.theme_classification` 不存在。

- [ ] **Step 3: 最小实现分类模块**

定义不可变 `MARKET_SIGNAL_CODES`、`is_market_signal(code)`、`exclude_market_signals()` 和 `only_market_signals()`。条件直接绑定 `Theme.code`，集合转为排序元组以保证生成参数稳定。

- [ ] **Step 4: 验证分类测试通过**

Run: `cd backend; python -m pytest tests/unit/test_theme_classification.py -q`

Expected: PASS。

### Task 2: 普通题材查询统一排除

**Files:**
- Modify: `backend/app/repositories/theme.py`
- Modify: `backend/tests/unit/test_theme_repository.py`

- [ ] **Step 1: 写失败测试**

捕获 `list_paginated` 的 count/data 语句及 `search`、`get_categories`、`get_ranking`、`stream_all` 的语句，断言均含市场表现排除条件；断言分页 count 子查询和数据查询口径一致。

- [ ] **Step 2: 验证测试在缺少排除条件时失败**

Run: `cd backend; python -m pytest tests/unit/test_theme_repository.py -q`

Expected: 新增断言 FAIL。

- [ ] **Step 3: 应用统一排除条件**

在五类普通查询的基础 `where` 中加入 `exclude_market_signals()`，不改变详情方法，以保留市场表现详情访问。

- [ ] **Step 4: 验证仓储测试通过**

Run: `cd backend; python -m pytest tests/unit/test_theme_repository.py -q`

Expected: PASS。

### Task 3: 市场表现后端接口

**Files:**
- Modify: `backend/app/repositories/theme.py`
- Modify: `backend/app/services/theme.py`
- Modify: `backend/app/api/theme.py`
- Modify: `backend/tests/unit/test_theme_repository.py`
- Modify: `backend/tests/unit/test_theme_service.py`
- Modify: `backend/tests/integration/test_theme_api.py`

- [ ] **Step 1: 写失败测试**

测试仓储 `get_market_signals()` 使用包含条件并按涨跌幅降序；服务返回 `ThemeRankingResponse`；`GET /api/v1/themes/market-signals` 返回数据且调用服务，不落入 `/{theme_id}` 校验。

- [ ] **Step 2: 验证缺少方法和路由导致测试失败**

Run: `cd backend; python -m pytest tests/unit/test_theme_repository.py tests/unit/test_theme_service.py tests/integration/test_theme_api.py -q`

Expected: FAIL，提示方法不存在或接口 422/404。

- [ ] **Step 3: 实现仓储、服务和静态路由**

仓储查询未删除且代码在集合内的记录，按 `rise_fall_pct DESC, heat_index DESC` 排序；服务复用 `ThemeRankingResponse`；API 静态路由声明在动态路由前。

- [ ] **Step 4: 验证后端相关测试通过**

Run: `cd backend; python -m pytest tests/unit/test_theme_classification.py tests/unit/test_theme_repository.py tests/unit/test_theme_service.py tests/integration/test_theme_api.py -q`

Expected: PASS。

### Task 4: 前端 API 契约

**Files:**
- Modify: `frontend/src/api/theme.ts`
- Modify: `frontend/src/api/theme.test.ts`

- [ ] **Step 1: 写失败测试**

调用期望的 `fetchMarketSignals()`，断言请求 `GET /themes/market-signals` 并原样返回 `ThemeRankingResponse`。

- [ ] **Step 2: 验证导出函数不存在导致测试失败**

Run: `cd frontend; npx vitest run src/api/theme.test.ts`

Expected: FAIL。

- [ ] **Step 3: 实现最小 API 函数**

复用 `apiClient` 和 `ThemeRankingResponse` 类型，不增加重复响应类型。

- [ ] **Step 4: 验证 API 测试通过**

Run: `cd frontend; npx vitest run src/api/theme.test.ts`

Expected: PASS。

### Task 5: 独立市场表现区域

**Files:**
- Create: `frontend/src/components/MarketSignalSection.tsx`
- Create: `frontend/src/components/MarketSignalSection.test.tsx`

- [ ] **Step 1: 写失败测试**

覆盖标题、名称、带正负号涨跌幅、股票数、点击回调、骨架、空数据文案“暂无市场表现数据”和失败文案“市场表现加载失败”。

- [ ] **Step 2: 验证组件不存在导致测试失败**

Run: `cd frontend; npx vitest run src/components/MarketSignalSection.test.tsx`

Expected: FAIL。

- [ ] **Step 3: 实现响应式紧凑网格**

使用 `section` 和无外层卡片的网格；每项是可点击按钮，显示名称、涨跌幅和股票数，正值红色、负值绿色、零值中性色；稳定最小高度并防止文本溢出。

- [ ] **Step 4: 验证组件测试通过**

Run: `cd frontend; npx vitest run src/components/MarketSignalSection.test.tsx`

Expected: PASS。

### Task 6: 仪表盘数据与更新联动

**Files:**
- Modify: `frontend/src/features/dashboard/ThemeDashboard.tsx`
- Modify: `frontend/src/features/dashboard/ThemeDashboard.test.tsx`

- [ ] **Step 1: 写失败测试**

模拟市场表现响应和普通题材列表 `total=279`，断言页面显示市场表现独立区域、统计显示 279 而非排行长度、点击进入详情；更新成功后排行、列表和市场表现均再次请求；市场表现失败不隐藏热门题材。

- [ ] **Step 2: 验证测试因缺少查询和区域而失败**

Run: `cd frontend; npx vitest run src/features/dashboard/ThemeDashboard.test.tsx`

Expected: 新增断言 FAIL。

- [ ] **Step 3: 实现四路查询和状态组合**

增加普通题材计数查询（`page_size: 1`）、市场表现查询和 `MarketSignalSection`；`QuickStats.totalThemes` 使用计数响应 `total`；更新和自动刷新并行刷新排行、涨跌、计数及市场表现；加载条和刷新按钮纳入市场表现状态。

- [ ] **Step 4: 验证仪表盘测试通过**

Run: `cd frontend; npx vitest run src/features/dashboard/ThemeDashboard.test.tsx`

Expected: PASS。

### Task 7: 格式化、回归和页面检查

**Files:**
- Modify only files changed above when formatters require it.

- [ ] **Step 1: 运行后端格式和静态检查**

Run: `cd backend; python -m black --check app/domain/theme_classification.py app/repositories/theme.py app/services/theme.py app/api/theme.py tests/unit/test_theme_classification.py tests/unit/test_theme_repository.py tests/unit/test_theme_service.py tests/integration/test_theme_api.py; python -m ruff check <same files>`

Expected: PASS；若仅格式失败，运行 Black 后重试。

- [ ] **Step 2: 运行前端针对性测试和检查**

Run: `cd frontend; npx vitest run src/api/theme.test.ts src/components/MarketSignalSection.test.tsx src/features/dashboard/ThemeDashboard.test.tsx; npx eslint src/api/theme.ts src/components/MarketSignalSection.tsx src/components/MarketSignalSection.test.tsx src/features/dashboard/ThemeDashboard.tsx src/features/dashboard/ThemeDashboard.test.tsx`

Expected: PASS。

- [ ] **Step 3: 运行相关后端测试集**

Run: `cd backend; python -m pytest tests/unit/test_theme_classification.py tests/unit/test_theme_repository.py tests/unit/test_theme_service.py tests/integration/test_theme_api.py -q`

Expected: PASS。

- [ ] **Step 4: 浏览器检查**

确认前后端服务可用后，在桌面和移动视口检查实际题材与市场表现分区、文本无重叠、项目可点击、更新反馈明确；记录任何既有构建或全量测试失败，不把无关改动纳入本次修复。

