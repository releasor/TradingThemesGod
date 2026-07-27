# 催化雷达设计

## 背景

题材详情已有 `theme_driver_events` 与洞察刷新，但缺少**跨题材**的催化横截面：盘中难以回答「今天哪些是新催化、哪些是旧闻复读、政策还是公司事件」。详情页同步爬虫还会占满单 worker。本设计落地独立路由 **催化雷达**，读库为主，分类规则打底、模型可选后台重标。

产品路线（本设计只实现催化雷达）：

| 顺序 | 页面 | 路由 | 本设计 |
|------|------|------|--------|
| 1 | 复盘台 | `/review` | 已交付 |
| 2 | 催化雷达 | `/catalysts` | **实现** |
| 3 | 题材挖掘 | `/mining` | 不做 |
| 4 | 主线图谱 | `/mainline-graph` | 不做 |

### 产品决策摘要

| 决策点 | 选择 |
|--------|------|
| 页面形态 | Nav Card「复盘研究」独立页 `/catalysts` |
| 布局 | 双栏：左时间流 + 右题材摘要 |
| 主数据 | `theme_driver_events` |
| 辅数据 | 右侧题材卡附带相关 `news_articles` 标题（不新爬） |
| 分类架构 | 事件表存当前标签 + `catalyst_classifications` 审计快照 |
| 分类产生 | 规则打底；有用户模型时后台增量重标 |
| Worker | 读 API 轻量；分类 ensure / 模型重标后台化 |

## 目标

1. 提供 `/catalysts` 双栏雷达：可按新鲜度、主体类型、题材、时间筛选事件流。
2. 为驱动事件打上 `freshness`（新催化/旧闻复读）与 `actor_type`（政策/公司/其他）。
3. 规则同步可跑；模型重标异步且失败不覆盖规则结果。
4. 打开雷达**不触发**全量网页爬虫；减轻详情页压力的产品替代入口。

## 范围

### 本次包含

- 迁移：`theme_driver_events` 增加分类列；新建 `catalyst_classifications`
- 规则分类器（可单测）+ 批处理/ensure
- 可选模型后台重标（登录且有默认模型）
- API：`/api/v1/catalysts/feed`、`/themes/{id}/summary`、`/classify/ensure`
- 前端双栏页 + Nav 入口
- 测试：规则、聚合 API、Nav、双栏空态/筛选

### 本次不包含

- 题材挖掘、主线图谱、自选
- 打开雷达即爬网或改详情洞察为同步长任务
- 向量数据库 / 全文检索引擎升级
- 推送通知、WebSocket
- 人工编辑分类 UI（可后续）

## 与已有文档关系

- **消费** `2026-07-20-theme-detail-insights-design.md` 的 `theme_driver_events` / `theme_profiles`，不改变洞察生成主流程；仅在事件落库或 ensure 时打分类。
- **衔接** `2026-07-26-review-desk-event-sourcing-design.md`：同属「复盘研究」Nav 组。
- 短线雷达里的「新闻时间催化」文案可链到本页，但不强制改看板结构。

## 总体架构

```text
theme_driver_events 写入/ensure
        │
        ▼
CatalystRuleClassifier → 更新事件当前标签
        │
        └─ append catalyst_classifications (method=rules)
        │
        ▼ (可选)
后台任务 Model reclassify → 更新当前标签 + append (method=model)
        │
        ▼
GET /catalysts/feed          左栏时间流
GET /catalysts/themes/{id}/summary  右栏 + 附带新闻标题
```

## 导航与路由

### Nav Card

在「复盘研究」分组追加：

```text
复盘研究
  - 复盘台 → /review
  - 催化雷达 → /catalysts
```

### 前端路由

| 路径 | 说明 |
|------|------|
| `/catalysts` | 默认左栏全市场流；query `themeId` 时右侧锁定题材 |
| `/catalysts?freshness=new&actor=policy` | 筛选深链 |

不要求登录即可浏览；**模型重标**需登录且已配置模型。规则 ensure 可不登录（或限制频率）。

## 双栏信息架构

### 左：时间流

- 条目：标题、摘要截断、题材名、发布时间、来源、`freshness` / `actor_type` 徽章、相关分
- 筛选：新鲜度、主体、题材 id、自/至时间、关键词（标题/摘要 contains）
- 分页：`limit` + `cursor`（`published_at,id`）或 offset；默认 30
- 点击：设置选中 `themeId` + 高亮该事件

### 右：题材摘要

- 题材名、链到 `/themes/:id`
- 若有轮动快照：阶段与强度（只读，缺则隐藏）
- 计数：近 7 日 new/replay、policy/company/other
- 该题材最近驱动事件（短列表）
- **附带新闻**：`news_articles` 中标题或正文含题材名（或已有题材关联若存在）的最近 N 条标题+链接+时间；**不调用爬虫**；无则空态

## 数据模型

### `theme_driver_events` 新增列

| 列 | 类型 | 说明 |
|----|------|------|
| `freshness` | `String(16)` | `new` / `replay` / `unknown`，默认 `unknown` |
| `actor_type` | `String(16)` | `policy` / `company` / `other` / `unknown`，默认 `unknown` |
| `classified_by` | `String(16)` | `rules` / `model` / null |
| `classified_at` | `DateTime(tz)` | 可空 |

索引：`(freshness, published_at)`、`(actor_type, published_at)` 便于筛选。

### `catalyst_classifications`

| 列 | 说明 |
|----|------|
| `id` | PK |
| `event_id` | FK → `theme_driver_events.id` ON DELETE CASCADE |
| `freshness` | 同上枚举 |
| `actor_type` | 同上枚举 |
| `method` | `rules` / `model` |
| `model_name` | 可空 |
| `confidence` | 0–100 可空 |
| `rationale` | 短文本可空 |
| `created_at` | 时间 |

索引：`(event_id, created_at)`。

## 规则分类器

纯函数模块（建议 `backend/app/services/catalyst_rules.py`），输入：当前事件 + 同题材近期事件摘要列表。

### 默认阈值

| 规则 | 默认 |
|------|------|
| 旧闻时间窗 | 同题材 **14** 个自然日内 |
| 标题相似 | 规范化后 token Jaccard ≥ **0.55**，或 `event_key` 相同 |
| 新催化 | 未命中旧闻，且 `published_at` 在查询窗内（展示层筛选） |
| 政策关键词 | 国务院、发改委、证监会、央行、工信部、财政部、政策、意见稿、规划、监管、部委 等 |
| 公司关键词 | 公告、业绩、中标、订单、回购、增持、减持、签约、落地、公司 等 |
| 来源启发 | 公告类来源偏 company；人民日报/新华社/部委站偏 policy |

冲突：政策与公司词同时命中 → `other`（或按来源加权；实现取 **来源优先，其次词数多者，平局 `other`**）。  
全无信号 → `unknown`。

每次规则写入：更新事件四列 + `catalyst_classifications` 一行（`method=rules`）。

## 模型重标

- 触发：`POST /classify/ensure` 且请求用户已登录有默认模型；或内部队列
- 候选：近 N 日（默认 7）且（`unknown` 或 `classified_by=rules`）
- 后台 `asyncio.create_task` + 独立 `AsyncSessionLocal`；**禁止**在 feed GET 内同步 LLM
- 成功：更新事件当前标签，`classified_by=model`，追加 classification
- 失败：保留原规则标签，可记日志；不 500 整个 ensure

## API

前缀：`/api/v1/catalysts`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/feed` | 查询参数：`freshness`, `actor_type`, `theme_id`, `q`, `from`, `to`, `limit`, `offset` |
| GET | `/themes/{theme_id}/summary` | 右栏 DTO |
| POST | `/classify/ensure` | body/query：`days=7`, `use_model=true`；先规则批处理，再按需入队模型 |

`feed` 项含：`event_id`, `theme_id`, `theme_name`, `title`, `summary`, `source`, `url`, `published_at`, `relevance_score`, `freshness`, `actor_type`, `classified_by`。

`summary` 含：题材信息、lifecycle 可选、分类计数、recent_events[]、news_headlines[]。

## 前端

- `frontend/src/features/catalysts/CatalystRadar.tsx` 等
- 左栏列表 + 筛选条；右栏 `CatalystThemeSummary`
- 进入页可静默 `classify/ensure`（规则 only，`use_model` 仅登录用户可选开关默认关，避免意外耗额度）
- 视觉遵循现有壳与 Card Nav

## 写入挂钩

- 洞察服务写入/更新 `theme_driver_events` 后调用规则分类（单条或小批量）
- 历史未分类：ensure 或一次性 backfill（ensure 覆盖近 N 日即可）

## 测试

- 规则：旧闻相似、政策/公司词、冲突、unknown
- Service：feed 筛选、summary 附带新闻空态
- API：200 / 筛选参数
- 前端：双栏渲染、筛选、Nav 链接

## 风险与降级

| 风险 | 处理 |
|------|------|
| driver 事件稀少 | 空态文案引导去题材详情刷新洞察；不自动爬 |
| 规则误标 | 允许 unknown；模型可纠；审计表可对照 |
| 新闻误匹配 | 仅标题/已有关联；标注「关键词匹配」 |
| LLM 堵 worker | 仅后台任务 |

## 验收标准

1. Nav 可进 `/catalysts`，复盘台入口仍在。  
2. 左栏可筛选 freshness/actor；右栏随选中题材更新并可能显示新闻标题。  
3. ensure 后近 N 日事件具备非空分类列（至少 rules）。  
4. `catalyst_classifications` 有对应审计行。  
5. feed/summary **不**发起外网爬取。  
6. 测试覆盖规则主路径与 API。

## 后续（本设计不实现）

- 题材挖掘（低位分支/补涨/隐性龙头）
- 主线图谱
- 人工纠正分类写入
- 催化与复盘台事件流打通展示
