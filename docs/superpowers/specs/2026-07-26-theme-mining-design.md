# 题材挖掘设计

## 背景

短线雷达已为题材提供生命周期与四维强度（见 `2026-07-25-theme-lifecycle-short-term-radar-design.md`），但缺少「在已有题材内」挖低位分支、补涨、隐性龙头的专用页。本设计落地独立路由 **题材挖掘**，三列看板 + 题材卡展开明细，结果日快照落库，可选模型点评。

| 顺序 | 页面 | 路由 | 本设计 |
|------|------|------|--------|
| 1 | 复盘台 | `/review` | 已交付 |
| 2 | 催化雷达 | `/catalysts` | 已交付 |
| 3 | 题材挖掘 | `/mining` | **实现** |
| 4 | 主线图谱 | `/mainline-graph` | 不做 |

### 产品决策摘要

| 决策点 | 选择 |
|--------|------|
| 布局 | 三列：低位分支 \| 补涨 \| 隐性龙头 |
| 结果单位 | 双层：题材卡 → 展开个股（可选概念节点标签） |
| 计算与存储 | 日快照落库 + 可选用户模型点评 |
| 架构 | `theme_mining_cards` + `theme_mining_members` + `theme_mining_notes` |
| 数据边界 | 只挖已有题材；不发明新题材；缺数据 degraded |

## 目标

1. `/mining` 三列展示当日（或指定交易日）挖掘题材卡。  
2. 规则引擎可解释输出三类候选及成份股 members。  
3. `POST /ensure` 重算并幂等写入快照；可读库不依赖打开页现算重负载。  
4. 登录用户可对单卡 ensure 点评（后台 LLM，失败不影响列表）。

## 范围

### 包含

- 迁移三表 + ORM/Repo/规则/Service/API
- 短线 refresh 成功后可选自动 ensure（失败吞掉）
- 前端三列双层页 + Nav
- 单元测试与冒烟

### 不包含

- 主线图谱页、自选、推送
- 打开页触发全市场爬虫
- 无强度/行情时伪造龙头或补涨

## 与已有文档关系

- **消费** 生命周期/强度：`sector_rotation_snapshots`、成分股 `stocks.rise_fall_pct` 等。  
- **可选消费** `concept_nodes` / `concept_node_stocks` 作 member 标签。  
- Nav 与复盘/催化同组「复盘研究」。

## 总体架构

```text
POST /mining/ensure  或  short-term refresh 挂钩
        │
        ▼
MiningRuleEngine（纯函数）← snapshots + 成分股指标
        │
        ▼
theme_mining_cards + theme_mining_members（幂等）
        │
        ▼
GET /mining/board
GET /mining/cards/{id}
        │
        ▼ (可选)
POST /mining/cards/{id}/note/ensure → 后台 LLM → theme_mining_notes
```

## 导航与路由

```text
复盘研究
  - 复盘台 → /review
  - 催化雷达 → /catalysts
  - 题材挖掘 → /mining
```

| 路径 | 说明 |
|------|------|
| `/mining` | 默认最近交易日三列 |
| `/mining?date=YYYY-MM-DD` | 指定日 |

浏览可不登录；**点评**需登录且有模型。

## UI

### 三列

每列标题 + 卡片列表（按 score/rank）：

- 题材名（链到详情）
- 阶段徽章、强度
- score、一句话 rationale
- 「展开」members 预览数
- 「点评」按钮（已登录）

### 展开层

- 个股：代码、名称、涨跌、score、role_tag  
- 若有 `concept_node_id`：显示节点名标签  
- degraded / missing_metrics 明示

## 数据模型

### `theme_mining_cards`

| 列 | 说明 |
|----|------|
| `id` | PK |
| `trade_date` | 交易日 |
| `theme_id` | FK themes |
| `mining_type` | `low_branch` / `catch_up` / `hidden_leader` |
| `score` | 0–100 |
| `rank` | 列内排序 |
| `lifecycle_stage` | 冗余快照 |
| `strength_score` | 冗余 |
| `rationale` | 中文短因 |
| `score_breakdown` | JSON |
| `degraded` | bool |
| `missing_metrics` | JSON list |

唯一：`uq_theme_mining_cards_date_theme_type (trade_date, theme_id, mining_type)`  
索引：`(trade_date, mining_type, rank)`

### `theme_mining_members`

| 列 | 说明 |
|----|------|
| `id` | PK |
| `card_id` | FK cards CASCADE |
| `stock_id` | FK stocks |
| `concept_node_id` | 可空 FK concept_nodes SET NULL |
| `score` | int |
| `rank` | int |
| `role_tag` | 如 `laggard` / `starter` / `shadow_leader` |
| `metrics` | JSON（涨跌分位等） |

唯一：`(card_id, stock_id)`；索引 `(card_id, rank)`

### `theme_mining_notes`

| 列 | 说明 |
|----|------|
| `id` | PK |
| `card_id` | FK |
| `user_id` | FK users |
| `status` | pending/running/success/failed |
| `content_md` | text |
| `model_name` | 可空 |
| `error` | 可空 |
| `created_at` / `updated_at` | |

唯一：`(card_id, user_id)`

## 规则引擎

模块：`backend/app/services/mining_rules.py`（纯函数）。

### 题材入池

优先：当日 `sector_rotation_snapshots` 中 stage ∈ {`fermentation`,`climax`,`divergence`} 或 `strength_score` ≥ 阈值（默认 45）的题材；不足时放宽到有快照题材 Top N（默认 40）。

### low_branch

- 题材强度中高、stage 非 ebb  
- 成分股按 `rise_fall_pct` 分位：取低于题材内 **40 分位** 且非跌停异常缺失者作为 members  
- 卡 score：题材强度 ×0.5 + 滞后个股数量分 ×0.5  
- 至少 2 只 member 才出卡

### catch_up

- 题材 stage 偏强；个股涨跌 >0 且仍低于题材中位数  
- 或近弱转正（若仅有当日数据，用 >0 且排名中后段）  
- members role=`starter`

### hidden_leader

- 使用快照 `leader_clarity_score` / `flow_score`（缺则 degraded）  
- 个股：题材内涨幅非 Top2，但（相对涨幅 + 热度代理）综合分靠前  
- 或成分股中「涨幅中等但所属节点/名称含龙头关键词」——**避免过拟合：以量化分位为主，关键词仅加分 ≤10**

### 缺数

无 `rise_fall_pct`：该题材跳过或 degraded 且不出卡；不写假涨跌。

## API

前缀：`/api/v1/mining`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/board` | `trade_date?` → `{ low_branch:[], catch_up:[], hidden_leader:[] }` 卡含 top 预览 members |
| GET | `/cards/{id}` | 全 members + 当前用户 note（若有） |
| POST | `/ensure` | `trade_date?` 重算；可匿名 |
| POST | `/cards/{id}/note/ensure` | 需登录；后台生成 |

`resolve_trade_date` 与短线一致。

## 挂钩

`ShortTermService.refresh_signals` 成功结束时 `try: MiningService.ensure(trade_date)` except log。

## 模型点评

输入：卡 rationale + members 摘要 + 题材阶段；输出短 Markdown；后台 `AsyncSessionLocal`；禁止堵 GET。

## 测试

- 规则：三类出卡/不出卡、缺涨跌 degraded  
- ensure 幂等  
- board 三列结构  
- Nav + 展开 UI  

## 风险

| 风险 | 处理 |
|------|------|
| 成分股无涨跌 | 跳过/degraded |
| 图谱缺失 | members 不挂 node，仍出个股 |
| ensure 慢 | Top N 题材限制；refresh 挂钩吞异常 |

## 验收

1. Nav 可进 `/mining`，三列有卡或明确空态。  
2. ensure 后三表有当日数据（有行情时）。  
3. 展开可见 members；点评登录可 ensure。  
4. 读 board 不爬网。  
5. 测试覆盖规则主路径。

## 后续

主线图谱页；人工纠正挖掘类型；与复盘台联动展示历史挖掘命中率。
