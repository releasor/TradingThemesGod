# 个人 AI OS 设计规格

**日期：** 2026-10-12  
**状态：** 已实现（期 1–3）

相关文档：

- 灵感来源总结：[`2026-10-12-shao-allen-justin-sun-podcast-summary.md`](./2026-10-12-shao-allen-justin-sun-podcast-summary.md)
- 产品需求清单：[`2026-10-12-personal-ai-os-prd-checklist.md`](./2026-10-12-personal-ai-os-prd-checklist.md)

## 目标

将工作区入口「应用 C」落地为独立应用 **个人 AI OS**（路径 `/os`）：用户可调人设、记忆策略、模块开关与模型偏好，获得带个人记忆的对话、生活日志日报与多模型决策参谋。

## 锁定决策

- 登录必填（`ProtectedRoute`）
- 与 Prompt 工作台数据隔离；仅共用 JWT + `ModelProvider` / LLM 适配层
- 记忆：固定档案 + 可检索笔记（SQL LIKE）
- 分期：1 对话/记忆/设置 → 2 日志/日报 → 3 多模型决策

## 路由

| Path | 说明 |
|------|------|
| `/os` | Shell，默认跳转 `/os/dashboard` |
| `/os/dashboard` | 个人仪表盘：汇总、钉选、优化指引 |
| `/os/chat` | 流式对话 |
| `/os/memory` | 档案 + 笔记 |
| `/os/settings` | 人设、记忆策略、模块、模型偏好、导出 |
| `/os/journal` | 饮食/训练/睡眠/日程 |
| `/os/reports` | 日报生成与反馈 |
| `/os/decisions` | 决策线程、上中下策 |

## API（`/api/v1/os`）

- `GET/PATCH /profile`
- `GET /dashboard` — 汇总概览 + 优化 tips + 钉选
- `GET/POST/PATCH/DELETE /dashboard/pins`；`DELETE .../by-source/{type}/{id}`
- `GET /export` — Markdown ZIP（档案/笔记/日志/日报/决策）
- `GET /decision-templates` — 「开图」脚手架模板
- `GET/POST/PATCH/DELETE /notes`
- `CRUD /chat/sessions` + `POST .../messages` + `.../messages/stream`
- `CRUD /journal`
- `GET /reports`、`POST /reports/generate`、`.../stream`、`POST .../feedback`
- `CRUD-ish /decisions`、`POST .../run`、`.../choose`、`POST /decisions/options/{id}/feedback`

关闭模块时对应 API 返回 403。

日报/决策反馈在 `apply_to_prompt=true` 时分别写入 `report_prompt_appendix` /
`decision_prompt_appendix`，并注入后续日报、决策与对话生成。

仪表盘优化指引按档案空缺、日志热身、多模型配置、反馈闭环等动态生成（参考播客「先攒数据 / 开图 / 人拍板 / 可迁移资产」）。

## 数据表

`os_profiles`（含 `decision_prompt_appendix`，迁移 `025`）、`os_dashboard_pins`（迁移 `026`）、`os_notes`、`os_chat_sessions`、`os_chat_messages`、`os_journal_entries`、`os_daily_reports`、`os_decision_threads`、`os_decision_runs`、`os_decision_options`（迁移 `024_create_personal_os_tables`）。

## 移动端

- `viewport-fit=cover` + safe-area 边距
- `< md`：底部图标导航；`≥ md`：顶栏 tabs
- 对话页手机用会话抽屉，输入框 `text-base` 避免 iOS 聚焦缩放
- 双栏页在窄屏纵向堆叠，主内容可滚动

## 非目标

可穿戴同步、第二套密钥、与 Prompt 会话合并、向量检索、计费、MD 文件夹双向同步。
