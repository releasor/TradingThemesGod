# AI 个股买入/持有研判报告 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 登录用户可对指定股票调用默认 LLM，结合市场上下文生成「买入/观望/回避 + 长短线适配」结论卡与完整报告，并按用户+股票缓存最近一份。

**Architecture:** 后端 `StockAiReportService` 聚合个股/短线/题材/新闻/一进二上下文，经 `ModelProviderService.adapter().complete(json_mode=True)` 抽取结构化 JSON，upsert 到 `stock_ai_reports`。前端 `/ai-analysis` 改为 GET 缓存 + POST 生成/强制刷新，展示结论卡与正文；规则模板降为可折叠参考。

**Tech Stack:** FastAPI、SQLAlchemy Async、Alembic、Pydantic v2、pytest、React、TanStack Query、Vitest。

**Spec:** `docs/superpowers/specs/2026-07-24-ai-stock-buy-hold-report-design.md`

---

## 文件结构

### 新建

- `backend/alembic/versions/014_create_stock_ai_reports.py`
- `backend/app/models/stock_ai_report.py`
- `backend/app/schemas/stock_ai_report.py`
- `backend/app/repositories/stock_ai_report.py`
- `backend/app/services/stock_ai_report.py`
- `backend/tests/unit/test_stock_ai_report_service.py`
- `backend/tests/integration/test_stock_ai_report_api.py`（若集成测环境可用；否则 API 单测 mock）
- `frontend/src/types/stock-ai-report.ts`
- `frontend/src/api/stock-ai-report.ts`
- `frontend/src/api/stock-ai-report.test.ts`

### 修改

- `backend/app/models/__init__.py` — 注册模型
- `backend/app/api/stock.py` — GET/POST ai-report
- `frontend/src/features/analysis/AiStockAnalysis.tsx` — 生成流与报告 UI
- `frontend/src/features/analysis/AiStockAnalysis.test.tsx` — 覆盖登录/409/缓存/渲染

---

### Task 1: 迁移 + ORM + Schema

**Files:** 上述 model / schema / migration / `__init__.py`

- [ ] **Step 1:** 新增 `StockAiReport` ORM（唯一 `(user_id, stock_code)`，JSON `sections`/`context_digest`，verdict 字符串，horizon 三列 Text，confidence int，full_report Text 等）。
- [ ] **Step 2:** Alembic `014_create_stock_ai_reports.py`（revision after `013`）。
- [ ] **Step 3:** Pydantic：`HorizonFit`、`HorizonSlot`、`StockAiReportSections`、`ExtractedStockAiReport`、`StockAiReportResponse`、`StockAiReportGenerateRequest`；固定 `DISCLAIMER` 常量。
- [ ] **Step 4:** 注册到 `models/__init__.py`。

### Task 2: Repository

**Files:** `backend/app/repositories/stock_ai_report.py` + 单测（可选内联于 service 测）

- [ ] `get(user_id, code)` / `upsert(...)` 更新全部报告字段与 `generated_at`。

### Task 3: Service（TDD）

**Files:** `stock_ai_report.py` service + `test_stock_ai_report_service.py`

- [ ] 测试：无默认模型 → 409；`force=False` 有缓存直接返回；模型返回合法 JSON → upsert；非法 JSON → 502 且不覆盖旧数据。
- [ ] 实现：`get_cached`、`generate(code, force)`；上下文构建（StockService、ShortTermService.overview、theme ranking/list、news list、FirstToSecond 可选）；截断；`parse_model_json`；映射 horizon fit 中文前缀写入列；响应带 disclaimer。

### Task 4: API

**Files:** `backend/app/api/stock.py` + 测试

- [ ] `GET /stocks/{code}/ai-report` → 缓存或 404
- [ ] `POST /stocks/{code}/ai-report` body `{force?: bool}` → generate
- [ ] `Depends(get_current_user)`

### Task 5: Frontend API + types

- [ ] `fetchStockAiReport(code)`、`generateStockAiReport(code, { force })`，timeout 300_000
- [ ] Vitest：路径与 timeout

### Task 6: Frontend UI

- [ ] 按钮「生成 AI 研判」；未登录提示；GET→展示 / 404→POST；重新生成 `force:true`；409 链到模型设置
- [ ] 结论卡 + full_report + sections；市场上下文折叠「规则汇总 · 非 AI 结论」
- [ ] 更新测试

### Task 7: 迁移跑通 + 冒烟

- [ ] `alembic upgrade head`（本地 DB）
- [ ] 相关 pytest / vitest 全绿

**Commits:** 按用户要求再提交；本计划步骤默认不自动 commit。

---

## Spec coverage checklist

| Spec 项 | Task |
|---------|------|
| stock_ai_reports 缓存 | 1–2 |
| GET/POST + force/409/502 | 3–4 |
| 结论卡 + 全文 + 上下文折叠 | 6 |
| 登录/无模型提示 | 6 |
| 免责声明 | 3,6 |
| 测试 | 3–6 |
