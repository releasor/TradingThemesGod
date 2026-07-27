# 复盘台（事件溯源）设计

## 背景

看板与短线雷达已能给出当日策略卡、候选与题材阶段，但缺少按交易日/题材回放「当时结论 → 后来涨跌」的闭环，规则难以迭代。规格 `2026-07-25-theme-lifecycle-short-term-radar-design.md` 将「复盘模式 + AI 题材日报」列为后续能力；本设计将其落地为 **Nav Card 可切换的独立页面**（不是首页，也不替换看板）。

同批产品路线（本设计只实现复盘台，其余各写各的规格与迭代）：

| 顺序 | 页面 | 路由（预定） | 本设计 |
|------|------|--------------|--------|
| 1 | 复盘台 | `/review` | **实现** |
| 2 | 催化雷达 | `/catalysts` | 不做 |
| 3 | 题材挖掘 | `/mining` | 不做 |
| 4 | 主线图谱 | `/mainline-graph` | 不做 |

自选工作台明确不做。

### 产品决策摘要

| 决策点 | 选择 |
|--------|------|
| 页面形态 | 独立路由，经 App Card Nav 切换进入 |
| 主时间轴 | 双模式：默认交易日轴，可切题材轴 |
| 数据架构 | 事件溯源：`review_runs` 外壳 + `review_events` 实体明细 |
| AI 题材日报 | 该日首次打开或盘后触发自动生成；失败降级为规则摘要 |
| 日报归属 | 登录且有用户模型 → 按 `user_id` 生成；否则仅规则摘要（可无 `user_id`） |
| 历史无事件 | 读现有短线/轮动快照表投影，标记 `degraded`，不伪造事件 |
| Worker 隔离 | 日报生成走后台任务；读聚合 API 保持轻量 |

## 目标

1. 提供 `/review` 复盘台：交易日轴 + 题材轴，展示策略卡结论、雷达候选、题材阶段迁移、实际涨跌验证。
2. 在 short-term refresh / signals refresh / overview analyze 等路径写入 `review_runs` + `review_events`，支持按 run 与实体回放。
3. 支持 AI 题材日报自动 ensure（首开/盘后），无模型或失败时规则摘要，结构化复盘始终可用。
4. Nav Card 增加「复盘研究」分组，本版只挂「复盘台 → /review」；催化/挖掘/图谱等各页落地后再往同组加链接，不挂空链。

## 范围

### 本次包含

- 迁移与模型：`review_runs`、`review_events`、`review_ai_reports`
- 写入挂钩：短线相关 refresh/analyze 成功与失败路径写 run；关键实体变更写 event
- API：`/api/v1/review/*` 日列表、日聚合、题材轴、日报 get/ensure
- 后台：日报生成任务（与请求线程解耦）
- 前端：`/review` 双模式页、Nav 入口、降级与日报状态展示
- 测试：事件写入、聚合投影、无事件降级、日报 ensure 降级、关键 UI

### 本次不包含

- 催化雷达、题材挖掘、主线图谱页面与其专用表
- 自选工作台
- 推送通知 / WebSocket 实时提醒
- 规则一键回测与收益曲线产品化
- 伪造无来源的行情或阶段
- 把复盘设为站点首页

## 与已有文档关系

- **消费** `2026-07-25-theme-lifecycle-short-term-radar-design.md` 与 `2026-07-21-short-term-opportunity-radar-design.md` 的信号/候选/轮动快照，不另建冲突口径。
- 看板 `MarketStrategyCard`、短线雷达区块 **保留**；复盘是只读回放与日报，不删除盘中入口。
- AI 调用沿用按用户 `model_providers` 的鉴权与配置（见 `2026-07-22-user-auth-model-settings-design.md`）。
- 概念知识图谱、催化分类等留给后续页面规格。

## 总体架构

```text
short-term refresh / signals refresh / overview analyze
        │
        ▼
review_runs (外壳: type/status/trade_date/source_status)
        │
        ├─ review_events: strategy_card
        ├─ review_events: candidate_upsert
        ├─ review_events: sector_stage_change
        ├─ review_events: emotion_snapshot
        ├─ review_events: signal_batch / quote_refresh
        │
        ▼
GET /review/days/{date}  ──投影──►  日复盘 DTO
GET /review/themes/{id}  ──投影──►  题材轴 DTO
        │
        ▼
POST /review/days/{date}/report/ensure
        │
        ├─ 已有报告 → 返回
        ├─ 有用户模型 → 入队生成 → review_ai_reports
        └─ 无模型/失败 → 规则摘要 + status=rule_fallback|failed
```

## 导航与路由

### Nav Card

在 `APP_CARD_NAV_ITEMS` 增加分组（文案可微调，语义不变）：

```text
复盘研究
  - 复盘台 → /review
```

催化雷达 / 题材挖掘 / 主线图谱落地后加入同组，本版不挂空链。

现有「题材看板」「题材分析」「设置」分组保留。

### 前端路由

| 路径 | 说明 |
|------|------|
| `/review` | 默认交易日轴；query `?date=YYYY-MM-DD` |
| `/review?themeId=` 或页内切换 | 题材轴；进入后加载近 N 日轨迹 |

不要求登录即可查看结构化复盘；**触发 LLM 日报**需登录且已配置模型（与现有 LLM 接口策略一致）。规则摘要无需登录。

## 双模式信息架构

### 交易日轴（默认）

1. 交易日选择器（仅列出有 run 或可降级投影的日期）
2. 当日 run 时间线（类型、状态、起止、缺失源）
3. 策略卡结论（来自最新成功 `strategy_card` 事件；无则降级现算/快照）
4. 雷达候选列表（当日 `candidate_upsert` 投影；可按策略类型分组）
5. 题材阶段迁移（相对前日 `sector_stage_change`：进入/离开高潮等）
6. 实际涨跌验证：候选股/焦点题材的当日收盘涨跌；若有次日数据则附「次日表现」
7. AI 题材日报区：ensure 状态（生成中 / 完成 / 规则摘要 / 失败）

### 题材轴

1. 题材选择（搜索或从日复盘点击题材进入）
2. 近 N 日（默认 10）阶段与强度轨迹
3. 窗口内命中的候选与相关 run 片段
4. 涨跌结果摘要
5. 一键跳回对应交易日轴

## 数据模型

### `review_runs`

| 字段 | 说明 |
|------|------|
| `id` | PK |
| `trade_date` | 交易日 |
| `run_type` | `signals_refresh` / `overview_analyze` / `quote_refresh` / `manual_backfill` 等 |
| `status` | `running` / `success` / `partial` / `failed` |
| `source_status` | JSON：各数据源状态 |
| `request_meta` | JSON：period、触发方等 |
| `started_at`, `finished_at` | 时间 |
| `created_at`, `updated_at` | 时间戳 |

索引：`(trade_date, started_at)`；`(run_type, trade_date)`。

### `review_events`

| 字段 | 说明 |
|------|------|
| `id` | PK |
| `run_id` | FK → `review_runs`，可空（仅降级回填时慎用；正常路径必填） |
| `trade_date` | 冗余便于按日查 |
| `event_type` | 见下 |
| `entity_type` | `market` / `theme` / `stock` / `candidate` / `batch` |
| `entity_id` | 可空；theme_id/stock_id/candidate 业务键 |
| `payload_json` | 事件体（策略卡字段、阶段前后值、候选分数等） |
| `occurred_at` | 事件时间 |
| `created_at` | 写入时间 |

索引：`(trade_date, event_type)`；`(run_id)`；`(entity_type, entity_id, trade_date)`。

**event_type 枚举（本期）：**

- `strategy_card`
- `candidate_upsert`
- `sector_stage_change`
- `emotion_snapshot`
- `signal_batch`
- `quote_refresh`

### `review_ai_reports`

| 字段 | 说明 |
|------|------|
| `id` | PK |
| `trade_date` | 交易日 |
| `user_id` | 可空；LLM 报告按用户；规则摘要可为 null |
| `status` | `pending` / `running` / `success` / `rule_fallback` / `failed` |
| `content_md` 或 `content_json` | 正文结构（摘要、主线、候选回顾、风险） |
| `model_name` | 可空 |
| `error` | 可空 |
| `source_run_ids` | JSON：生成所用 run 列表 |
| `created_at`, `updated_at` | 时间戳 |

唯一约束：`(trade_date, user_id)`（`user_id` NULL 时用应用层保证「全局规则摘要一份」或 partial unique，按 MySQL 能力选型）。

## 写入挂钩

在下列路径 **开始** 建 `review_runs(status=running)`，**结束** 更新 status，并写入对应 events：

1. 短线信号 refresh（`signal_batch` 等）
2. overview / 策略分析（`strategy_card`、`emotion_snapshot`）
3. 板块轮动/生命周期落库后（`sector_stage_change`：仅当阶段或强度档相对前日变化，或首次出现）
4. 候选 upsert（`candidate_upsert`）
5. 策略相关行情刷新（`quote_refresh`，可合并为 batch 摘要避免事件爆炸）

原则：

- 失败也要结束 run（`failed`/`partial`），便于复盘看到「那天刷新挂了」。
- 事件 payload 只存可解释结论与关键指标，不存整页 HTML。
- 禁止用「今天的 live 行情」回填历史日的涨跌验证字段。

## API

前缀：`/api/v1/review`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/days?from=&to=` | 有 run 或可降级的交易日列表 |
| GET | `/days/{date}` | 日复盘聚合 DTO |
| GET | `/themes/{theme_id}?days=10` | 题材轴 |
| GET | `/days/{date}/report` | 当前用户日报；无则 404 或空对象 |
| POST | `/days/{date}/report/ensure` | 幂等：有则返回；无则入队/同步规则摘要 |

`GET /days/{date}` 响应要点：

- `trade_date`, `degraded`, `missing_sources`
- `runs[]`
- `strategy_card`（投影）
- `candidates[]`
- `stage_transitions[]`
- `performance`（候选/题材涨跌验证；缺数据则 null + 原因）
- `report_summary`（若已有报告则短摘要）

非交易日：`resolve_trade_date` 滚到最近有效交易日并标注。

## AI 日报

### 触发

1. 用户打开某交易日复盘且尚无可用报告 → 前端调 `ensure`  
2. 若已有调度器：交易日收盘后批量 `ensure`（无用户上下文则只写规则摘要；有活跃用户模型配置的可按用户队列，**第一期可只做首开 ensure + 全局规则摘要盘后任务**）

### 生成约束

- 输入仅限：当日事件投影 + 候选 + 阶段迁移 + 已有涨跌验证字段  
- 不得编造未提供的价格或阶段  
- 超时/模型错误 → `failed` 或写入 `rule_fallback` 规则摘要，页面不空白  

### 与 Worker

- `ensure` 若需 LLM：立即返回 `status=pending|running`，后台任务写库；前端轮询 `GET report` 或短轮询 ensure  
- **禁止**在 uvicorn 单 worker 内同步长爬虫 + 长 LLM 串联（沿用既有卡死教训）

## 前端 UI

- 新 feature：`frontend/src/features/review/`  
- 复用现有策略卡展示组件（只读）、候选列表样式、阶段徽章  
- 顶部：模式切换（交易日 / 题材）+ 日期或题材选择  
- 明确展示 `degraded` 与缺失源  
- 日报区：生成中骨架、正文 Markdown/结构化块、错误与「规则摘要」标签  

视觉：遵循现有应用壳与 Card Nav，不另做营销落地页。

## 测试

- 单元：事件写入、阶段变更去重、日聚合投影、无事件降级、日报 ensure 幂等与 fallback  
- API：日复盘 200/降级字段、题材轴、ensure 状态机  
- 前端：双模式切换、空日、日报 pending/success/fallback  

## 风险与降级

| 风险 | 处理 |
|------|------|
| 历史无事件 | 快照表投影 + `degraded` |
| 事件量过大 | `quote_refresh`/`signal_batch` 用摘要事件；候选按条但限制 Top N 详情 |
| LLM/爬虫堵死 API | 日报与重任务后台化 |
| 次日涨跌尚未就绪 | `performance.next_day` 为 null，不显示假数据 |
| 多用户日报成本 | 仅登录用户 ensure LLM；盘后默认可只跑规则摘要 |

## 验收标准

1. Nav Card「复盘研究」可进入 `/review`，看板首页不变。  
2. 交易日轴可见：runs、策略卡、候选、阶段迁移、涨跌验证（有则显示）。  
3. 题材轴可见近 N 日轨迹与关联候选，可跳回交易日。  
4. refresh/analyze 后 `review_runs`/`review_events` 有对应记录。  
5. 无事件历史日可打开且 `degraded=true`。  
6. `ensure`：有模型可生成用户日报；无模型或失败得规则摘要；结构化复盘仍完整。  
7. 测试覆盖主路径；不实现催化/挖掘/图谱/自选。

## 后续页面（本设计不实现）

1. **催化雷达**（P3）：新催化 / 旧闻复读 / 政策 vs 公司事件；独立路由；减轻详情页同步爬虫压力。  
2. **题材挖掘**（P1）：低位分支、补涨、隐性龙头。  
3. **主线图谱**（P2 + 概念知识图谱）：主线 vs 支线与概念从属研究页。  

上述页面各自开规格，仍通过 Nav Card「复盘研究」（或后续更名的研究分组）切换，不塞进看板第一屏。
