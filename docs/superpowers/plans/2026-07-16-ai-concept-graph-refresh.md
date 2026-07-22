# AI Concept Graph Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为所有题材增加用户可配置的多协议模型服务，并基于真实公开资料增量更新细分知识图谱。

**Architecture:** 模型配置由数据库和应用级加密服务管理；协议适配器统一输出文本或模型列表。图谱刷新服务组合安全网页抓取、严格 JSON 抽取、证据校验和幂等增量写入，前端通过设置页和题材页调用。

**Tech Stack:** FastAPI、SQLAlchemy、MySQL、httpx、cryptography、React、TanStack Query、Zustand、Vitest。

---

### Task 1: 模型配置与加密存储

**Files:**
- Create: `backend/app/models/model_provider.py`
- Create: `backend/app/schemas/model_provider.py`
- Create: `backend/app/services/secret_store.py`
- Create: `backend/app/services/model_provider.py`
- Create: `backend/app/api/model_provider.py`
- Create: `backend/alembic/versions/009_create_model_providers.py`
- Test: `backend/tests/unit/test_model_provider_service.py`

- [ ] 先编写 API Key 加密、更新时保留旧 Key、响应脱敏和默认配置唯一性的失败测试。
- [ ] 运行定向测试，确认因服务不存在而失败。
- [ ] 实现模型、迁移、加密存储、服务和 REST API。
- [ ] 运行测试并确认通过。

### Task 2: 多协议模型适配器

**Files:**
- Create: `backend/app/integrations/llm/base.py`
- Create: `backend/app/integrations/llm/openai_compatible.py`
- Create: `backend/app/integrations/llm/anthropic.py`
- Create: `backend/app/integrations/llm/gemini.py`
- Create: `backend/app/integrations/llm/ollama.py`
- Create: `backend/app/integrations/llm/factory.py`
- Test: `backend/tests/unit/test_llm_adapters.py`

- [ ] 编写各协议 URL、鉴权头、模型列表和 JSON 文本读取的失败测试。
- [ ] 运行测试确认失败原因是适配器缺失。
- [ ] 实现统一 `complete`、`list_models` 和 `test_connection` 接口。
- [ ] 运行测试确认通过。

### Task 3: 真实资料抓取与图谱抽取

**Files:**
- Create: `backend/app/services/web_research.py`
- Create: `backend/app/schemas/concept_refresh.py`
- Create: `backend/app/services/concept_graph_refresh.py`
- Modify: `backend/app/repositories/concept_graph.py`
- Modify: `backend/app/api/theme.py`
- Test: `backend/tests/unit/test_web_research.py`
- Test: `backend/tests/unit/test_concept_graph_refresh.py`

- [ ] 编写 SSRF 阻断、正文清理、严格 JSON、来源引用和股票白名单的失败测试。
- [ ] 运行测试确认失败。
- [ ] 实现搜索、网页抓取、模型提示词、结果校验和增量合并。
- [ ] 增加单题材和批量刷新接口。
- [ ] 运行相关测试确认通过。

### Task 4: 设置页与刷新交互

**Files:**
- Create: `frontend/src/api/model-provider.ts`
- Create: `frontend/src/features/settings/ModelSettings.tsx`
- Create: `frontend/src/features/settings/ModelSettings.test.tsx`
- Modify: `frontend/src/api/theme.ts`
- Modify: `frontend/src/features/themes/ThemeDetail.tsx`
- Modify: `frontend/src/features/themes/ThemeDetail.test.tsx`
- Modify: `frontend/src/features/themes/ThemeLibrary.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] 编写设置保存、连接测试、单题材刷新和无配置引导的失败测试。
- [ ] 运行测试确认失败。
- [ ] 实现设置页、导航入口、刷新状态和批量操作。
- [ ] 运行前端定向测试确认通过。

### Task 5: 迁移、预置与端到端验证

**Files:**
- Modify: `backend/.env.example`
- Modify: `backend/app/main.py`

- [ ] 执行 Alembic 迁移并写入无密钥本地预设。
- [ ] 运行 Ruff、后端定向测试和前端定向测试。
- [ ] 重启前后端服务。
- [ ] 用 Playwright 验证设置页、未配置提示、移动端布局和控制台。
