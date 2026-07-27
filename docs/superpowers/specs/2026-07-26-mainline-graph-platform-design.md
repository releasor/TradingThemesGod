# 主线图谱平台设计

## 背景

短线底座已有 `mainline_score`、生命周期与概念知识树（`concept_nodes`），但缺少**跨题材主线 vs 支线叙事图**独立研究页。本设计落地 **主线图谱平台**（路线 C）：版本化叙事、可编辑边、规则/模型建议边、双模（市场叙事 | 题材概念树），并规划多日回放动画为二期。

| 顺序 | 页面 | 路由 | 状态 |
|------|------|------|------|
| 1–3 | 复盘 / 催化 / 挖掘 | `/review` `/catalysts` `/mining` | 已交付 |
| 4 | 主线图谱 | `/mainline-graph` | **本设计** |

### 产品决策摘要

| 决策点 | 选择 |
|--------|------|
| 产品档位 | C：完整图谱平台（分期，不砍愿景） |
| 交互 | 双模；叙事模式 = ECharts 关系图 + 右侧详情抽屉 |
| 边来源 | 规则共现为主 + 可选模型建议边 + **人工编辑** |
| 持久化 | 版本化图快照（非仅现算） |
| 一期 | 版本化叙事图 + 可编辑边 + 概念树模式 + 规则 ensure + 模型建议（后台） |
| 二期 | 多日回放动画、版本 diff、批量导入导出 |

## 目标（一期）

1. `/mainline-graph` 双模页面挂入 Nav「复盘研究」。  
2. 叙事模式：读当日（或指定版本）nodes/edges；点节点打开抽屉（阶段/强度/支线/进概念树）。  
3. 规则 ensure 按成分股重叠等写建议边；模型可后台补建议边。  
4. 登录用户可对**可编辑草稿版本**增删改边权；发布为正式版本。  
5. 概念树模式：复用既有 `concept_graph` API，叠题材阶段/强度摘要。

## 范围

### 一期包含

- 表：`mainline_graph_versions`、`mainline_graph_nodes`、`mainline_graph_edges`
- 规则建边 + ensure；可选模型建议边（`status=suggested`）
- 人工编辑 API（仅 draft 版本）
- 读图 API + 概念树模式代理
- 前端双模 + ECharts + 抽屉 + 基础编辑（加边/删边/调权）
- 测试

### 一期不包含（二期）

- 多日时间轴动画回放
- 版本可视化 diff、导出 PNG/JSON 包
- 全局协同锁 / OT
- 自动交易或收益承诺

### 永不做

- 无重叠证据时伪造主线边
- 打开页同步全量爬虫/长 LLM

## 与已有文档关系

- 消费 `sector_rotation_snapshots.mainline_score` / lifecycle / strength  
- 消费 `theme_stocks` 算重叠；概念树见 `2026-07-16-concept-knowledge-graph-design.md`  
- Nav 与复盘/催化/挖掘同组

## 总体架构

```text
POST /mainline-graph/ensure
        │
        ▼
规则：Top 主线题材 × 重叠度 → edges (method=rules, status=active)
可选：模型建议边 → status=suggested
        │
        ▼
mainline_graph_versions (published | draft)
  ├─ nodes (theme_id, scores snapshot)
  └─ edges (from, to, weight, method, status)
        │
        ▼
GET /mainline-graph/view?trade_date|version_id
人工：POST/PATCH/DELETE edges on draft → publish
概念树：GET /themes/{id} concept_graph（已有）
```

## 导航与路由

```text
复盘研究
  - 复盘台 / 催化雷达 / 题材挖掘 / 主线图谱 → /mainline-graph
```

Query：`?mode=narrative|concept&date=&versionId=&themeId=`

## 双模 UI

### 叙事模式（默认）

- 左：ECharts `graph`（力导向或 circular）；节点大小∝ mainline/strength；颜色∝ lifecycle  
- 边：active 实线；suggested 虚线（可一键采纳到 draft）  
- 右抽屉：题材名、阶段、强度、mainline_score、相连支线表、链到详情/概念树模式  
- 顶栏：日期、版本选择、Ensure、新建草稿、发布、编辑开关

### 概念树模式

- 选题材（或从抽屉跳入）  
- 复用详情页概念树组件（抽公共）；顶部显示当日阶段/强度条  
- 无图谱空态，不编造节点

## 数据模型

### `mainline_graph_versions`

| 列 | 说明 |
|----|------|
| `id` | PK |
| `trade_date` | 交易日 |
| `kind` | `auto` / `draft` / `published` |
| `title` | 可空 |
| `status` | `open` / `published` / `archived` |
| `parent_version_id` | 可空（草稿来源） |
| `created_by` | user_id 可空（auto 为空） |
| `published_at` | 可空 |
| `meta` | JSON |
| timestamps | |

索引：`(trade_date, kind, status)`

规则：每个 `trade_date` 可有多个 draft；**至多一个**当前 `published`（发布时归档旧 published）。

### `mainline_graph_nodes`

| 列 | 说明 |
|----|------|
| `id` | PK |
| `version_id` | FK CASCADE |
| `theme_id` | FK |
| `mainline_score` | int |
| `strength_score` | int |
| `lifecycle_stage` | str |
| `role` | `mainline` / `branch` / `other` |
| `payload` | JSON 可空 |

唯一：`(version_id, theme_id)`

### `mainline_graph_edges`

| 列 | 说明 |
|----|------|
| `id` | PK |
| `version_id` | FK |
| `from_theme_id` | FK |
| `to_theme_id` | FK |
| `weight` | float 0–1 |
| `method` | `rules` / `model` / `manual` |
| `status` | `active` / `suggested` / `rejected` |
| `rationale` | text |
| `created_by` | 可空 |

唯一：`(version_id, from_theme_id, to_theme_id)`（同向一条；无向图可存 from&lt;to 规范化或保留有向「主→支」）

**有向约定：** `from` = 主线侧，`to` = 支线侧（mainline_score 更高者优先为 from，平局按 theme_id）。

## 规则建边

模块：`mainline_graph_rules.py`

1. 取当日快照 Top N（默认 30）按 `mainline_score`。  
2. 前 K（默认 5）标 `role=mainline`，其余候选 `branch`。  
3. 对每对 (main, other) 算成分股 Jaccard；≥ **0.12**（可配）建边，weight=Jaccard。  
4. 同向强度相关加分（可选，≤0.15）。  
5. 写入 `auto` 版本（或覆盖当日 auto）；不删除用户 `published`。

缺成分股：degraded，少边，不编造。

## 模型建议边

- ensure 时 `use_model=true` 且登录：后台对「高分无边」对调用 LLM，写入 `suggested`  
- 用户在 UI「采纳」→ 复制到 draft 为 `manual`/`model` active  

## API（`/api/v1/mainline-graph`）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/view` | `trade_date` 或 `version_id` → nodes+edges+version meta |
| GET | `/versions` | 按日列出版本 |
| POST | `/ensure` | 规则生成/刷新 `auto` 版本；可选模型建议 |
| POST | `/versions` | 从 auto/published 克隆 `draft`（需登录） |
| PATCH | `/versions/{id}/edges` | draft 上 upsert/delete 边（需登录） |
| POST | `/versions/{id}/publish` | draft → published（需登录） |
| POST | `/edges/{id}/accept` | suggested → 写入当前 draft |
| GET | `/themes/{id}/concept` | 代理或组装概念树 + 当日强度条 |

## 前端

- `features/mainline-graph/MainlineGraphPage.tsx`  
- `MainlineNarrativeChart.tsx`（echarts-for-react）  
- `MainlineDrawer.tsx`、`ConceptTreeMode.tsx`（抽复用 ThemeDetail 树）  
- 编辑：选两节点加边、边权滑条、删边、采纳建议  

## 挂钩

短线 `refresh_signals` 成功后可选 `MainlineGraphService.ensure(auto)`（吞异常）。

## 二期（多日动画）

- `GET /playback?from=&to=` 返回逐日 node/edge diff  
- 前端时间轴 + ECharts 过渡；只读 published/auto  

## 测试

- 规则 Jaccard / 主从方向  
- ensure 幂等 auto  
- draft 编辑与 publish 唯一 published  
- view API；前端模式切换与空态  

## 风险

| 风险 | 处理 |
|------|------|
| 重叠过密 | Top N + Jaccard 阈值 + 每主线最多 M 条边 |
| 编辑冲突 | 一期单用户 draft；乐观锁 `updated_at` |
| ECharts 性能 | 节点 ≤40；超出分页/过滤 |

## 验收（一期）

1. Nav 可进 `/mainline-graph`，双模可切。  
2. ensure 后 auto 版本可 view；图与抽屉可用。  
3. 登录可建 draft、改边、发布；suggested 可采纳。  
4. 概念树模式有数据题材可展开，无数据空态。  
5. 读 view 不爬网、不同步长 LLM。  

## 后续

二期动画与版本 diff；与复盘台联动「当日主线叙事」嵌入。
