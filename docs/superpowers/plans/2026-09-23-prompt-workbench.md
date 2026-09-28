# Prompt 工作台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有工程中交付可登录使用的「Prompt 工作台」（`/prompt`）：设计、优化、Prompt 库、自由聊天，复用 TradingThemesGod 的模型设置与 JWT 鉴权。

**Architecture:** 后端新增 `/api/v1/prompt/*`（按 `user_id` 隔离）+ Alembic 表；LLM 一律经现有 `build_llm_adapter` + 用户 `ModelProvider`。前端新增 `features/prompt-workbench`，挂在项目入口；UI 复用 GlowCard / 主题体系。第一版 LLM 调用使用现有 `complete(..., json_mode=False)`（各协议已支持）；流式可二期在适配器加 `stream`，API 形状预留不影响。

**Tech Stack:** FastAPI、SQLAlchemy async、Alembic、httpx LLM adapters、React 19、React Router 7、TanStack Query、Zustand（轻量模型选择）、Vite。

**Spec:** `docs/superpowers/specs/2026-09-23-prompt-workbench-design.md`

---

## File map

### Backend (create)

| File | Responsibility |
|------|----------------|
| `backend/alembic/versions/023_create_prompt_workbench_tables.py` | 建表迁移 |
| `backend/app/models/prompt_workbench.py` | ORM：`PromptItem`、`PromptChatSession`、`PromptChatMessage`、`PromptOptimizeRun` |
| `backend/app/schemas/prompt_workbench.py` | Pydantic 请求/响应 |
| `backend/app/services/prompt_llm.py` | 解析用户模型 + 调用 `complete` |
| `backend/app/services/prompt_templates.py` | Smart/框架/设计 的 system 提示（无外部品牌词） |
| `backend/app/services/prompt_library.py` | Prompt 库 CRUD |
| `backend/app/services/prompt_optimize.py` | 设计/优化/迭代/双测 |
| `backend/app/services/prompt_chat.py` | 聊天会话与消息 |
| `backend/app/api/prompt_workbench.py` | 路由聚合 |
| `backend/tests/unit/test_prompt_*.py` | 单测 |

### Backend (modify)

| File | Change |
|------|--------|
| `backend/app/models/__init__.py` | 导出新模型 |
| `backend/app/main.py` | `include_router(prompt_workbench_router, prefix="/api/v1")` |

### Frontend (create)

| File | Responsibility |
|------|----------------|
| `frontend/src/features/prompt-workbench/PromptWorkbenchShell.tsx` | Tab 壳 + 模型选择 |
| `frontend/src/features/prompt-workbench/pages/*.tsx` | Design / Optimize / Library / Chat |
| `frontend/src/features/prompt-workbench/api/*.ts` | API client |
| `frontend/src/features/prompt-workbench/domain/frameworks.ts` | 框架元数据 |
| `frontend/src/features/prompt-workbench/domain/variables.ts` | `{{var}}` 解析 |
| `frontend/src/features/prompt-workbench/stores/modelSelection.ts` | 所选 `provider_id` |
| `frontend/src/features/prompt-workbench/*.test.ts(x)` | 前端单测 |

### Frontend (modify)

| File | Change |
|------|--------|
| `frontend/src/App.tsx` | `/prompt/*` 路由 + lazy |
| `frontend/src/features/launch/projectEntries.ts` | 入口改为 Prompt 工作台 → `/prompt` |

---

### Task 1: DB 迁移与 ORM

**Files:**
- Create: `backend/alembic/versions/023_create_prompt_workbench_tables.py`
- Create: `backend/app/models/prompt_workbench.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: 写迁移**（`down_revision = "022_themes_unique_source_code"`）

表：

1. `prompt_items`：`id BIGINT PK AI`，`user_id FK users CASCADE`，`title VARCHAR(200)`，`body TEXT`，`category VARCHAR(100) NULL`，`tags JSON NOT NULL`，`enabled BOOL`，`pinned BOOL`，`sort_order INT`，`created_at`/`updated_at` timestamptz；index `(user_id, pinned, sort_order)`
2. `prompt_chat_sessions`：`id`，`user_id`，`title VARCHAR(200)`，`provider_id BIGINT NULL`，timestamps
3. `prompt_chat_messages`：`id`，`session_id FK CASCADE`，`role VARCHAR(20)`，`content TEXT`，`created_at`；index `session_id`
4. `prompt_optimize_runs`：`id`，`user_id`，`source TEXT`，`result TEXT`，`mode VARCHAR(40)`，`framework VARCHAR(40) NULL`，`extra_goal TEXT NULL`，`versions JSON`，timestamps

字符集：`utf8mb4` / `utf8mb4_0900_ai_ci`，InnoDB（与现有迁移一致）。

- [ ] **Step 2: 写 ORM**（`TimestampMixin` + `Base`，字段与上表一致；`tags`/`versions` 用 `JSON`）

- [ ] **Step 3: 导出模型**

在 `backend/app/models/__init__.py` 增加 import 与 `__all__` 项。

- [ ] **Step 4: 跑迁移**

```bash
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Expected: 升级到 `023`，无错误。

- [ ] **Step 5: Commit**（仅当用户要求提交时执行）

```bash
git add backend/alembic/versions/023_create_prompt_workbench_tables.py backend/app/models/prompt_workbench.py backend/app/models/__init__.py
git commit -m "feat(backend): add prompt workbench tables"
```

---

### Task 2: Prompt 库 API（TDD）

**Files:**
- Create: `backend/app/schemas/prompt_workbench.py`
- Create: `backend/app/services/prompt_library.py`
- Create: `backend/app/api/prompt_workbench.py`（先挂库路由）
- Create: `backend/tests/unit/test_prompt_library.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/unit/test_prompt_library.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_create_prompt_item_sets_user_id():
    from app.services.prompt_library import PromptLibraryService
    from app.schemas.prompt_workbench import PromptItemCreate

    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    svc = PromptLibraryService(session, user_id=7)
    payload = PromptItemCreate(
        title="写作",
        body="为 {{audience}} 写一段话：{{content}}",
        category="写作",
        tags=["draft"],
    )
    # 实现后：result.user_id == 7 且 title 正确
    result = await svc.create(payload)
    assert result.title == "写作"
    assert result.user_id == 7
```

- [ ] **Step 2: 跑测确认失败**

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests/unit/test_prompt_library.py -v
```

Expected: FAIL（模块不存在或断言失败）。

- [ ] **Step 3: 实现 schema + service + router**

`PromptItemCreate` / `PromptItemUpdate` / `PromptItemResponse` 字段对齐 ORM。

Service 方法：`list(q, category, tag, enabled)`、`create`、`get`、`update`、`delete`；更新/删除必须校验 `user_id`，否则 404。

Router：

```python
router = APIRouter(prefix="/prompt", tags=["prompt"])

@router.get("/items", response_model=list[PromptItemResponse])
@router.post("/items", response_model=PromptItemResponse, status_code=201)
@router.get("/items/{item_id}", ...)
@router.put("/items/{item_id}", ...)
@router.delete("/items/{item_id}", status_code=204)
```

`main.py`：

```python
from app.api.prompt_workbench import router as prompt_workbench_router
# ...
app.include_router(prompt_workbench_router, prefix="/api/v1")
```

- [ ] **Step 4: 跑测通过**

```bash
.\.venv\Scripts\python.exe -m pytest tests/unit/test_prompt_library.py -v
```

Expected: PASS。

- [ ] **Step 5: Commit**（用户要求时）

---

### Task 3: LLM 调用与模板

**Files:**
- Create: `backend/app/services/prompt_templates.py`
- Create: `backend/app/services/prompt_llm.py`
- Create: `backend/tests/unit/test_prompt_templates.py`
- Create: `backend/tests/unit/test_prompt_llm.py`

- [ ] **Step 1: 模板单测**

```python
from app.services.prompt_templates import build_optimize_system

def test_smart_system_mentions_clarity():
    text = build_optimize_system(mode="smart", framework=None, extra_goal="更短")
    assert "清楚" in text or "清晰" in text
    assert "更短" in text

def test_crispe_system_includes_role_sections():
    text = build_optimize_system(mode="framework", framework="CRISPE", extra_goal=None)
    assert "CRISPE" in text.upper() or "Role" in text or "角色" in text
```

- [ ] **Step 2: 实现 `prompt_templates.py`**

导出：

- `build_design_system()` / `build_design_user(goal, notes)`
- `build_optimize_system(mode, framework, extra_goal)` / `build_optimize_user(source)`
- `build_iterate_user(current, instruction)`
- `FRAMEWORKS = ("CRISPE", "CO-STAR", "APE", "BROKE", "TRACE", "RTF")`

文案禁止出现 `Prizm` 等第三方品牌词。

- [ ] **Step 3: 实现 `prompt_llm.py`**

```python
async def resolve_adapter(session, user_id: int, provider_id: int | None) -> BaseLLMAdapter:
    # 查 ModelProvider：归属 user、enabled；未传则 is_default
    # 解密 key/headers，build_llm_adapter(...)
    # 无可用 → HTTPException(400, "请先在模型设置中配置可用模型")

async def run_completion(adapter, system: str, user: str) -> str:
    return await adapter.complete(system, user, json_mode=False, reasoning=False)
```

复用 `ModelProviderService` 的解密逻辑或只读查询 + `SecretStore`（不要复制密钥到响应）。

- [ ] **Step 4: `test_prompt_llm` 用 mock adapter，断言走 `complete(..., json_mode=False)`**

- [ ] **Step 5: 跑测 PASS 后按需提交**

---

### Task 4: 设计 / 优化 / 测试 API

**Files:**
- Modify: `backend/app/schemas/prompt_workbench.py`
- Create: `backend/app/services/prompt_optimize.py`
- Modify: `backend/app/api/prompt_workbench.py`
- Create: `backend/tests/unit/test_prompt_optimize.py`

- [ ] **Step 1: Schema**

```python
class DesignRequest(BaseModel):
    goal: str
    notes: str | None = None
    provider_id: int | None = None

class OptimizeRequest(BaseModel):
    source: str
    mode: Literal["smart", "framework"] = "smart"
    framework: str | None = None
    extra_goal: str | None = None
    provider_id: int | None = None
    persist: bool = True

class IterateRequest(BaseModel):
    run_id: int | None = None
    current: str
    instruction: str
    provider_id: int | None = None

class TestPromptsRequest(BaseModel):
    prompt_a: str
    prompt_b: str
    user_message: str
    provider_id: int | None = None

class TextResult(BaseModel):
    result: str
    run_id: int | None = None

class DualTestResult(BaseModel):
    output_a: str
    output_b: str
```

- [ ] **Step 2: Service**

- `design` → templates + `run_completion`
- `optimize` → 校验 framework ∈ FRAMEWORKS；可选写入 `PromptOptimizeRun`（`versions=[{"result": ...}]`）
- `iterate` → 追加 versions；更新 result
- `dual_test` → 两次 `run_completion`：system=各自 prompt，user=`user_message`

- [ ] **Step 3: Routes**

```
POST /prompt/design → TextResult
POST /prompt/optimize → TextResult
POST /prompt/optimize/iterate → TextResult
POST /prompt/test → DualTestResult
GET  /prompt/optimize/runs/{run_id} → 详情（属主校验）
```

- [ ] **Step 4: 单测 mock `run_completion`，覆盖 smart / 非法 framework 400 / dual_test 两次调用**

- [ ] **Step 5: 按需提交**

---

### Task 5: 聊天 API

**Files:**
- Create: `backend/app/services/prompt_chat.py`
- Modify: `backend/app/api/prompt_workbench.py`、`schemas`
- Create: `backend/tests/unit/test_prompt_chat.py`

- [ ] **Step 1: Schema** — `ChatSessionCreate/Update/Response`，`ChatMessageCreate`（`content`），`ChatMessageResponse`

- [ ] **Step 2: Service**

- sessions CRUD（user 隔离）
- `list_messages(session_id)`
- `send_message(session_id, content, provider_id?)`：
  1. 写入 user message
  2. 组装 history（system 固定短指令 + 历史轮次，截断最近 N=20）
  3. `run_completion`
  4. 写入 assistant message 并返回

第一版用单次 `complete`（非 SSE）。前端显示 loading。

- [ ] **Step 3: Routes**

```
GET/POST /prompt/chat/sessions
PATCH/DELETE /prompt/chat/sessions/{id}
GET /prompt/chat/sessions/{id}/messages
POST /prompt/chat/sessions/{id}/messages → ChatMessageResponse（assistant）
```

- [ ] **Step 4: 单测属主校验 + send 写入两条消息**

- [ ] **Step 5: 按需提交**

---

### Task 6: 前端壳、路由、入口

**Files:**
- Create: `frontend/src/features/prompt-workbench/PromptWorkbenchShell.tsx`
- Create: `frontend/src/features/prompt-workbench/stores/modelSelection.ts`
- Create: `frontend/src/features/prompt-workbench/pages/PlaceholderPages.tsx`（临时四页壳，后续任务替换）
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/features/launch/projectEntries.ts`
- Create: `frontend/src/features/prompt-workbench/PromptWorkbenchShell.test.tsx`

- [ ] **Step 1: `modelSelection` zustand**

```ts
interface State {
  providerId: number | null
  setProviderId: (id: number | null) => void
}
```

- [ ] **Step 2: Shell**

- `NavLink` 到 `design|optimize|library|chat`
- `useQuery(['model-providers'], fetchModelProviders)`，下拉选 enabled 项；默认 `is_default`
- Link「模型设置」→ `/settings/models`
- `<Outlet />`
- 包在布局内，使用现有边距/Glow 风格

- [ ] **Step 3: App 路由**

```tsx
const PromptWorkbenchShell = lazy(() =>
  import('@/features/prompt-workbench/PromptWorkbenchShell').then(m => ({
    default: m.PromptWorkbenchShell,
  }))
)
// ...
<Route
  path="/prompt"
  element={
    <ErrorBoundary>
      <ProtectedRoute>
        <PromptWorkbenchShell />
      </ProtectedRoute>
    </ErrorBoundary>
  }
>
  <Route index element={<Navigate to="optimize" replace />} />
  <Route path="design" element={<DesignPage />} />
  <Route path="optimize" element={<OptimizePage />} />
  <Route path="library" element={<LibraryPage />} />
  <Route path="chat" element={<ChatPage />} />
</Route>
```

- [ ] **Step 4: 入口**

```ts
{
  id: 'prompt-workbench',
  name: 'Prompt 工作台',
  description: '设计、优化并管理 Prompt，自由聊天；模型与题材台共用设置',
  to: '/prompt',
  ariaLabel: '进入 Prompt 工作台',
  badge: '应用',
},
```

删除或保留「应用 B」占位（删除 B，保留 C 即将推出）。

- [ ] **Step 5: 测试入口 link `href=/prompt`；Shell 渲染四个 Tab**

```bash
cd frontend
npx vitest run src/features/prompt-workbench/PromptWorkbenchShell.test.tsx src/features/launch/ProjectLaunchPage.test.tsx
```

- [ ] **Step 6: 按需提交**

---

### Task 7: 前端 — 我的 Prompt 库

**Files:**
- Create: `frontend/src/features/prompt-workbench/api/library.ts`
- Create: `frontend/src/features/prompt-workbench/domain/variables.ts`
- Create: `frontend/src/features/prompt-workbench/domain/variables.test.ts`
- Create: `frontend/src/features/prompt-workbench/pages/LibraryPage.tsx`
- Create: `frontend/src/features/prompt-workbench/components/VariableFillDialog.tsx`

- [ ] **Step 1: `extractVariables(body: string): string[]`**

正则：`/\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}/g`，去重保序。

`fillVariables(body, values: Record<string, string>): string`

- [ ] **Step 2: API**

`listPromptItems`、`createPromptItem`、`updatePromptItem`、`deletePromptItem` → `/api/v1/prompt/items`

- [ ] **Step 3: LibraryPage UI**

- 搜索框、分类/标签筛选
- 列表卡片：标题、摘要、置顶/启用、操作（复制 / 填变量复制 / 编辑 / 删除 / 送到优化）
- 「新建」表单：title、body、category、tags（逗号分隔）
- 「送到优化」：`navigate('/prompt/optimize', { state: { source: body } })`

- [ ] **Step 4: variables 单测 + Library 冒烟测（mock API）**

- [ ] **Step 5: 按需提交**

---

### Task 8: 前端 — 优化页

**Files:**
- Create: `frontend/src/features/prompt-workbench/api/optimize.ts`
- Create: `frontend/src/features/prompt-workbench/domain/frameworks.ts`
- Create: `frontend/src/features/prompt-workbench/pages/OptimizePage.tsx`
- Create: `frontend/src/features/prompt-workbench/OptimizePage.test.tsx`

- [ ] **Step 1: frameworks 常量**

```ts
export const OPTIMIZE_FRAMEWORKS = [
  { id: 'CRISPE', label: 'CRISPE', hint: '角色、背景、任务、格式与示例' },
  // CO-STAR, APE, BROKE, TRACE, RTF
] as const
```

- [ ] **Step 2: OptimizePage**

- 原文 textarea；读取 `location.state.source`
- 模式：Smart | 框架 select；Smart 时显示「补充目标」；框架时隐藏补充目标
- 按钮：优化 / 迭代（有结果后）/ 复制 / 存库 / 高级·双测
- 左右对照：原文 | 结果
- 版本历史列表（本地 state，来自 iterate 累加；若有 `run_id` 可再拉）
- `providerId` 来自 modelSelection store，一并传 API
- loading / error Toast（`useToastContext`）

- [ ] **Step 3: 组件测 — 选 CRISPE 后补充目标输入不在文档中**

- [ ] **Step 4: 按需提交**

---

### Task 9: 前端 — 设计页

**Files:**
- Create: `frontend/src/features/prompt-workbench/api/design.ts`
- Create: `frontend/src/features/prompt-workbench/pages/DesignPage.tsx`

- [ ] **Step 1: `POST /prompt/design` client**

- [ ] **Step 2: UI** — goal、notes、生成、可编辑结果、复制、存库、送到优化

- [ ] **Step 3: 按需提交**

---

### Task 10: 前端 — 自由聊天

**Files:**
- Create: `frontend/src/features/prompt-workbench/api/chat.ts`
- Create: `frontend/src/features/prompt-workbench/pages/ChatPage.tsx`
- Create: `frontend/src/features/prompt-workbench/components/InsertPromptPopover.tsx`

- [ ] **Step 1: chat API client**（sessions + messages）

- [ ] **Step 2: ChatPage**

- 左栏会话列表（新建/重命名/删除）
- 右栏消息 + 输入框；发送后 loading 至 assistant 返回
- 「从库插入」：选条目 → 变量对话框 → 插入输入框
- URL `?session=` 同步当前会话

- [ ] **Step 3: 按需提交**

---

### Task 11: 联调验收

**Files:** 无新文件；修 bug only

- [ ] **Step 1: 迁移 + 重启后端**

```bash
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
# uvicorn 已在 8000 则依赖 reload；否则重启
```

- [ ] **Step 2: IronBee 验收脚本（浏览器）**

1. 打开 `http://localhost:5173/` → 见「Prompt 工作台」卡片  
2. 进入 `/prompt`（未登录应跳登录；登录后进 optimize）  
3. 模型设置已有默认模型时：优化一段短文，得到结果  
4. 存库 → Library 可见 → 变量 Prompt 可复制  
5. 设计页生成 → 聊天页发一条消息  
6. 页面文案搜索无 `Prizm`

- [ ] **Step 3: 跑相关单测**

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests/unit/test_prompt_*.py -v
cd ../frontend
npx vitest run src/features/prompt-workbench src/features/launch/ProjectLaunchPage.test.tsx
```

- [ ] **Step 4: 对照 spec §8 验收清单打勾；缺口记入跟进**

---

## Spec coverage check

| Spec 项 | Task |
|---------|------|
| 路由 `/prompt/*` + Tab | 6 |
| 设计 | 4, 9 |
| 优化 + 框架 + 迭代 + 双测 | 4, 8 |
| Prompt 库 + 变量 | 2, 7 |
| 自由聊天 | 5, 10 |
| 共用模型设置 | 3, 6 |
| 后端存库/聊天 | 1, 2, 5 |
| 无会员/插件/品牌词 | 全文约束 + Task 11 |
| 入口页 | 6 |
| 登录保护 | 6 `ProtectedRoute` |

## Decisions locked in plan

- LLM **非流式** `complete`（全协议可用）；二期再加 SSE  
- 分类为 **字符串字段**，不做独立 categories 表  
- JSON **导入导出** 不做（符合 spec 第一版）  
- 优化 run **可选持久化**（`persist` 默认 true）

---
