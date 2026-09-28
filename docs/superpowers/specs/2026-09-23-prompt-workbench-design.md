# Prompt 工作台设计

日期：2026-09-23  
状态：已确认方向，待实现计划

## 1. 目标

在现有 TradingThemesGod 前端工程中新增独立应用 **Prompt 工作台**，覆盖参考站网页侧核心能力（设计 / 优化 / Prompt 库 / 自由聊天），**不包含**会员、付费、Chrome 插件，以及任何第三方品牌文案。

约束：

- 自用：登录后使用
- 模型：与 TradingThemesGod **共用**现有「模型设置」与 `ModelProvider` / `build_llm_adapter`
- 数据：Prompt 库与聊天记录存后端 MySQL，按用户隔离
- UI：沿用现有设计系统（GlowCard、主题切换、暗色模式等）
- 入口：项目导航页增加「Prompt 工作台」→ `/prompt`

## 2. 非目标

- 浏览器插件（一键优化、`/p`、悬浮球、写回第三方输入框）
- 会员 / 套餐 / CDK / 用量计费
- 独立模型密钥体系或独立登录体系
- 公开分享 / 协作编辑 / 多租户组织

## 3. 信息架构与路由

| 路径 | 模块 |
|------|------|
| `/prompt` | 默认重定向到 `/prompt/optimize` |
| `/prompt/design` | 设计 Prompt |
| `/prompt/optimize` | 优化 Prompt |
| `/prompt/library` | 我的 Prompt |
| `/prompt/chat` | 自由聊天（可带 `?session=`） |

壳层：

- 顶部 Tab：设计 | 优化 | 我的 Prompt | 自由聊天
- 模型选择器：读取用户已启用的 `model_providers`，默认选 `is_default`
- 「模型设置」链到现有 `/settings/models`
- 未登录访问 `/prompt/*` → `/login?from=...`（与现有鉴权一致）

项目入口（`projectEntries.ts`）：

- 将「应用 B」替换为可进入的「Prompt 工作台」→ `/prompt`
- 「应用 C」可继续保留为即将推出占位

## 4. 功能规格

### 4.1 设计 Prompt

- 输入：任务目标（必填）、可选补充约束（受众、语气、输出格式等）
- 动作：调用默认/所选模型，生成一份可复用 Prompt
- 结果区：可编辑；「复制」「保存到我的 Prompt」「送到优化」
- 不强制框架；系统提示词内置「写出清晰、可复用、可含 `{{变量}}`」指引

### 4.2 优化 Prompt

- 输入：原始 Prompt（必填）
- 方式：
  - **Smart**（默认）：保留原意，表达更清楚、完整、好执行；可附加一句补充目标
  - 命名框架：CRISPE、CO-STAR、APE、BROKE、TRACE、RTF（选中后隐藏 Smart 补充目标，改用框架结构）
- 可选：自定义目标（与命名框架互斥展示规则同参考站网页：命名框架时以框架为主）
- 运行：流式输出优化结果；失败可重试
- 对照：左右并排「原文 | 优化结果」
- 迭代：基于当前结果再提修改指令；本次会话内保留版本历史（至少内存 + 可选持久化 run）
- 高级：
  - **测试 Prompt**：同一用户消息分别跑「原文」与「当前优化版」，两栏对照模型输出
- 结果动作：复制、保存到库、替换为下一次优化的输入

### 4.3 我的 Prompt 库

- CRUD：标题、正文、分类、标签（多选字符串）、启用/停用、置顶
- 列表：搜索（标题/正文）、按分类/标签筛选；置顶优先，组内可自定义排序（`sort_order`）
- 变量：正文支持 `{{name}}`；调用时弹表单填必填项，解析后复制到剪贴板
- 行操作：复制、编辑、删除、送到优化（带入正文）、启用/停用、置顶
- 导入导出（网页侧可选增强）：第一版不做 JSON 导入导出；若实现成本低可二期补

### 4.4 自由聊天

- 多会话：新建、重命名、删除、列表
- 消息：流式回复；停止生成；失败提示
- 可从「我的 Prompt」插入（含变量填表后再插入）
- 使用当前选中的模型提供商；与优化/设计共用选择器状态（前端 store 或 URL 无关的全局 session 态）

## 5. 后端设计

### 5.1 API 前缀

全部挂在 `/api/v1/prompt`，**强制登录**（`get_current_user`）。

建议端点：

**库**

- `GET /prompts` — 列表（q、category、tag、enabled）
- `POST /prompts`
- `GET /prompts/{id}`
- `PUT /prompts/{id}`
- `DELETE /prompts/{id}`
- `POST /prompts/{id}/reorder` — 可选；或 PUT 带 `sort_order` / `pinned`

**分类**（轻量）

- 第一版：分类为自由字符串字段即可，列表接口返回 distinct categories
- 若需规范化：`prompt_categories` 表（user_id, name, sort_order）

**设计 / 优化 / 测试（LLM）**

- `POST /design` — body: goal, notes?, provider_id? → stream 或一次性文本
- `POST /optimize` — body: source, mode (smart|framework), framework?, extra_goal?, provider_id? → stream
- `POST /optimize/iterate` — body: current, instruction, history?, provider_id? → stream
- `POST /test` — body: prompt_a, prompt_b, user_message, provider_id? → 两项结果（可并行）

**聊天**

- `GET /chat/sessions`
- `POST /chat/sessions`
- `PATCH /chat/sessions/{id}`
- `DELETE /chat/sessions/{id}`
- `GET /chat/sessions/{id}/messages`
- `POST /chat/sessions/{id}/messages` — stream（SSE 或现有项目惯用方式）

模型解析：

1. 若传 `provider_id`：校验归属当前用户且 enabled  
2. 否则：取该用户 `is_default=true` 的提供商  
3. 无可用模型 → 400，提示去 `/settings/models` 配置  

复用：`app.integrations.llm.factory.build_llm_adapter` + SecretStore 解密密钥。不新增模型配置表。

### 5.2 数据模型（MySQL）

`prompt_items`

| 字段 | 说明 |
|------|------|
| id | PK |
| user_id | FK users |
| title | 标题 |
| body | 正文（可含 `{{var}}`） |
| category | 可空字符串 |
| tags | JSON 数组 |
| enabled | bool |
| pinned | bool |
| sort_order | int |
| created_at / updated_at | |

`prompt_chat_sessions`

| 字段 | 说明 |
|------|------|
| id | PK |
| user_id | FK |
| title | |
| provider_id | 可空，记录创建时选用 |
| created_at / updated_at | |

`prompt_chat_messages`

| 字段 | 说明 |
|------|------|
| id | PK |
| session_id | FK |
| role | user / assistant / system |
| content | text |
| created_at | |

`prompt_optimize_runs`（可选，第一版建议保留便于刷新不丢）

| 字段 | 说明 |
|------|------|
| id | PK |
| user_id | FK |
| source | 原文 |
| result | 最新结果 |
| mode / framework / extra_goal | |
| versions | JSON 数组（迭代历史） |
| created_at / updated_at | |

Alembic 迁移纳入 `backend/alembic/versions/`。

### 5.3 系统提示与框架

后端内置模板（纯功能文案，无外部品牌名）：

- Smart、各命名框架的 system / developer 指令
- 设计 Prompt 的 system 指令
- 测试时仅把「待测 Prompt」作为 system 或首条，再喂用户测试消息

流式：优先 SSE（`text/event-stream`），与前端 `fetch` ReadableStream 对接；若现有 AI 报告接口有既定模式则对齐之。

## 6. 前端设计

目录：`frontend/src/features/prompt-workbench/`

建议结构：

```
prompt-workbench/
  PromptWorkbenchShell.tsx   # Tab 壳 + 模型选择
  pages/DesignPage.tsx
  pages/OptimizePage.tsx
  pages/LibraryPage.tsx
  pages/ChatPage.tsx
  api/*.ts
  domain/frameworks.ts       # 框架元数据
  domain/variables.ts        # {{var}} 解析
  components/...
```

状态：

- 模型选择：轻量 zustand 或 React context（仅 Prompt 工作台内）
- 库列表：react-query
- 优化会话：页面本地 state + 可选后端 run id

鉴权：路由外包 `ProtectedRoute`（与设置页一致）。

## 7. 安全与权限

- 所有 prompt API 校验 `user_id`
- 不在日志中打印完整 API Key 或用户 Prompt 明文超长内容（可截断）
- CORS / JWT 沿用现有配置
- 无公开匿名调用 LLM 的接口

## 8. 验收标准

1. 项目入口可进入 `/prompt`，四 Tab 可切换  
2. 未配置模型时，设计/优化/聊天给出明确引导至模型设置  
3. 优化：Smart + 至少一个命名框架可出结果，左右对比可见  
4. 高级双版本测试可对原文与优化结果分别出回复  
5. 库：新建、编辑、搜索、变量填表复制、送到优化  
6. 聊天：多会话、流式回复、从库插入  
7. 文案与代码中无第三方品牌词  
8. 模型调用实际走用户已保存的 `model_providers`

## 9. 实现分期建议（仍属同一产品第一版交付）

虽用户要求一次上齐四件套，实施时可按依赖顺序提交，避免大爆炸：

1. 迁移 + 库 CRUD API/UI  
2. LLM 流式基础设施 + 优化页  
3. 设计页 + 测试对照  
4. 聊天会话  
5. 入口页接线与联调  

每阶段保持可手动验证。

## 10. 决议记录

| 项 | 选择 |
|----|------|
| 形态 | 仅网页工作台 |
| 范围 | 四件套一次做齐 |
| 存储 | 后端 DB |
| 名称/路径 | Prompt 工作台 / `/prompt` |
| 品牌 | 无第三方品牌词 |
| UI | 沿用 TradingThemesGod 设计系统 |
| 模型 | 共用现有模型设置 |
