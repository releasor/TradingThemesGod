# 用户登录与按账号模型配置设计

## 目标

- 开放注册：用户名 + 密码
- JWT Bearer 认证
- 仅 `model_providers` 按用户隔离；题材/行情数据全局共享
- LLM 相关 API 需登录

## 数据模型

- `users`: id, username (unique), password_hash, timestamps
- `model_providers.user_id`: FK → users.id，每用户仅一个 `is_default=true`

## API

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `/api/v1/model-providers/*` 需登录，按 user_id 过滤
- 概念图/洞察/一进二 LLM 接口需登录

## 前端

- `/login`, `/register`
- `/settings/models` 需登录
- `apiClient` 自动附加 Bearer token
