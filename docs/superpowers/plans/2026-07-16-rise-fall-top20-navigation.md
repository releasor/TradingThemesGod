# Rise/Fall Top 20 Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将首页涨跌幅榜单扩展为 Top 20，并支持点击任一板块进入对应详情页。

**Architecture:** 图表组件保持路由无关，通过可选回调返回点击板块 ID；仪表盘负责数据请求和页面导航。ECharts 数据项携带 ID，纵轴标签点击通过榜单名称映射到 ID。

**Tech Stack:** React 19、TypeScript、ECharts、React Router、TanStack Query、Vitest、Testing Library

---

### Task 1: 图表 Top 20 与点击事件

**Files:**
- Modify: `frontend/src/components/charts/ThemeRiseFallBar.tsx`
- Test: `frontend/src/components/charts/ThemeRiseFallBar.test.tsx`

- [ ] **Step 1: 写失败测试**

在 ECharts mock 中捕获 `option` 与 `onEvents`，断言图表最多包含 20 条数据，并模拟柱体与纵轴标签点击，断言 `onThemeClick` 收到对应板块 ID。

- [ ] **Step 2: 运行测试确认失败**

Run: `pnpm exec vitest run src/components/charts/ThemeRiseFallBar.test.tsx`

Expected: FAIL，因为当前组件仍截取 10 条且没有点击回调。

- [ ] **Step 3: 写最小实现**

增加 `onThemeClick?: (themeId: number) => void`，截取前 20 条，为柱体数据附加 `themeId`，添加 ECharts `click` 事件处理，并将图表高度调整为 520px。

- [ ] **Step 4: 运行测试确认通过**

Run: `pnpm exec vitest run src/components/charts/ThemeRiseFallBar.test.tsx`

Expected: PASS。

### Task 2: 仪表盘请求与导航接线

**Files:**
- Modify: `frontend/src/features/dashboard/ThemeDashboard.tsx`
- Test: `frontend/src/features/dashboard/ThemeDashboard.test.tsx`

- [ ] **Step 1: 写失败测试**

断言 `fetchThemes` 使用 `page_size: 20`，标题显示 `涨跌幅 Top 20`；从图表 mock 触发板块 ID 后，断言导航到 `/themes/:id` 并携带首页来源状态。

- [ ] **Step 2: 运行测试确认失败**

Run: `pnpm exec vitest run src/features/dashboard/ThemeDashboard.test.tsx`

Expected: FAIL，因为当前请求和标题仍为 10，且未向图表传递点击回调。

- [ ] **Step 3: 写最小实现**

将查询键、请求条数及标题改为 20，并把 `handleThemeClick` 传给 `ThemeRiseFallBar`。

- [ ] **Step 4: 运行测试确认通过**

Run: `pnpm exec vitest run src/features/dashboard/ThemeDashboard.test.tsx`

Expected: PASS。

### Task 3: 完整验证

**Files:**
- Verify: `frontend/src/components/charts/ThemeRiseFallBar.tsx`
- Verify: `frontend/src/features/dashboard/ThemeDashboard.tsx`

- [ ] **Step 1: 运行全部前端测试**

Run: `pnpm exec vitest run`

Expected: 全部测试通过。

- [ ] **Step 2: 运行构建**

Run: `pnpm build`

Expected: TypeScript 与 Vite 构建通过。

- [ ] **Step 3: 运行 ESLint**

Run: `pnpm lint`

Expected: 无 ESLint 错误或警告。
