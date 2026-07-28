# Tushare 前端数据源配置设计

**日期：** 2026-07-28  
**状态：** 待实现  
**范围：** 设置 → 数据源页面对 Tushare 启用开关与 Token 的读写、测试与竞速生效

## 背景

Tushare 当前仅能通过后端环境变量（`TUSHARE_*`）配置，改完需重启进程，且 Token 明文存在 `.env`。用户需要在前端设置中完成启用与 Token 配置，并支持探活测试。

## 目标

1. 新增设置子页「数据源」`/settings/integrations`（需登录）。
2. 页面提供 Tushare：**启用开关、Token、保存、测试连接**。
3. 配置持久化到数据库；Token 使用现有 `SecretStore` 加密。
4. 爬虫 / 全量竞速优先读取 DB 配置，无记录时回退 `.env`；保存后无需重启即可生效。
5. GET 接口不返回 Token 明文，仅返回 `has_token`；提交空 Token 表示保留原值。

## 非目标

- 不在本页暴露高级项（`TUSHARE_API_URL`、`TUSHARE_CONCEPT_APIS` 等），仍仅 `.env`。
- 不引入管理员角色；与现有日历同步一致，任意登录用户可改全局配置。
- 不迁移/自动清空现有 `.env` Token（可作为初始回退来源）。
- 本迭代不加入雪球 Cookie 等其他数据源 UI（页面可预留扩展位，但不实现）。

## 方案

采用 **数据库单例行 + SecretStore**，与交易日历 meta、模型凭据加密模式对齐。

### 数据模型

表 `tushare_settings`（单例 `id = 1`）：

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | INT PK | 固定为 1 |
| `enabled` | BOOL | 是否启用 |
| `token_encrypted` | TEXT NULL | Fernet 密文；空表示未配置 |
| `updated_at` | DATETIME | 更新时间 |
| `updated_by` | INT NULL | 可选，记录操作用户 |

### 运行时解析顺序

`resolve_tushare_runtime()`：

1. 若存在 DB 行：使用 `enabled` + 解密后的 token（若密文为空则 token 视为空）。
2. 否则回退 `Settings.TUSHARE_ENABLED` / `Settings.TUSHARE_TOKEN`。
3. `tushare_ready()` ≡ `enabled and token.strip()`。
4. 高级参数（API URL、concept APIs 等）始终来自 env `Settings`。

`tushare_scraper` 与 `full_race.default_full_race_sources()` 改为调用上述解析，禁止直接依赖进程启动时缓存的 env 作为唯一来源。

### API（均需 JWT）

前缀：`/api/v1/integrations/tushare`

| 方法 | 路径 | 行为 |
|------|------|------|
| GET | `/` | 返回 `{ enabled, has_token, updated_at }`，不含明文 token |
| PUT | `/` | Body `{ enabled, token? }`；`token` 省略或 `""` 保留原密文；写入加密后落库 |
| POST | `/test` | 使用当前生效凭据（请求体可选临时 token）调用轻量 Tushare 接口探活；返回成功/失败与可读错误（含权限不足提示） |

### 前端

- `SettingsSubnav` / `AppCardNav` 增加「数据源」→ `/settings/integrations`。
- `App.tsx` 增加受保护路由。
- 新页 `IntegrationsSettings`：GlowCard「Tushare」含开关、密码输入、保存、测试；展示 `has_token` 状态文案（已配置 / 未配置）。
- API 客户端：`frontend/src/api/integrations.ts`。

### 安全

- Token 落库前经 `SecretStore.encrypt`；磁盘密钥复用 `MODEL_SECRET_KEY` / `.model-secret.key`。
- 响应永不回传明文 token。
- 测试接口错误信息可包含 Tushare 业务错误码摘要，不得回显完整 token。

## 验收

1. 未登录访问 `/settings/integrations` 被重定向登录。
2. 登录后可开关启用、填写 Token、保存；刷新后开关状态保留，`has_token=true`，输入框不回填明文。
3. 空 Token 再保存不会清空已有密文。
4. 「测试连接」在有效 Token 时成功（或明确返回积分/权限错误）；无效 Token 失败可读。
5. `enabled+token` 就绪时，全量竞速默认源列表包含 `tushare`；关闭启用后列表不再包含，无需重启后端。
6. 无 DB 行时仍可使用 `.env` 中的 Tushare 配置作为回退。

## 主要改动文件

- Backend：model / alembic / schemas / service / api；`tushare_scraper.py`、`full_race.py`；单测
- Frontend：`IntegrationsSettings.tsx`、`integrations.ts`、`SettingsSubnav`、`AppCardNav`、`App.tsx`
