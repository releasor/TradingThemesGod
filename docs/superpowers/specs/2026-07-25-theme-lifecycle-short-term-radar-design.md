# 题材生命周期与短线雷达全量落地设计

## 背景

看板已有策略卡、一进二、热门题材和题材详情热度，但：

- 短线信号未持久化（无涨停/炸板/龙虎榜日表）；
- 题材没有统一的生命周期与短线强度语言；
- `2026-07-21-short-term-opportunity-radar-design.md` 已设计表结构与雷达 UI，但尚未建迁移；现有 `/api/v1/short-term/overview` 等多为现算。

本次把「短线雷达全量底座」与「题材生命周期 + 强度仪表」合成一个可交付版本，作为后续主线图谱、催化雷达、题材挖掘 B、自选、复盘的数据地基。

### 产品决策摘要

| 决策点 | 选择 |
|--------|------|
| 产品档位 | 完整短线仪表：五阶段 + 四维强度 + 近 10 日轨迹 |
| 指标数据 | 真短线信号（非代理指标） |
| 采集范围 | 短线雷达全量表 |
| 交付切法 | 一次做满：底座 + 雷达 UI + 生命周期/仪表 |
| UI 落点 | 看板 + 详情都做满；题材库带阶段列 |
| 架构路径 | 扩展现有 `/api/v1/short-term` 模块，单一数据真相源 |

题材挖掘定位为后续 P1：**在已有题材内**挖低位分支、补涨、隐性龙头（本版只提供可复用的阶段与强度字段，不实现挖掘 UI）。

## 目标

1. 落地短线日信号全量表，支持刷新、幂等写入、降级标记。
2. 规则引擎写出可解释的轮动快照与一进二候选（改读库，不再只靠现算）。
3. 为每个覆盖题材按交易日打上：萌芽 / 发酵 / 高潮 / 分歧 / 退潮。
4. 输出四维强度：涨停质量、回流、辨识度龙头、跟风宽度（0–100，可解释）。
5. 看板完整短线雷达 UI；题材卡/题材库显示阶段；详情页完整仪表 + 近 10 日轨迹。

## 范围

### 本次包含

- 迁移与模型：`daily_stock_signals`、`dragon_tiger_entries`、`sector_rotation_snapshots`（含生命周期与强度字段）、`short_term_signal_runs`、`short_term_candidates`
- 采集器：涨停/炸板/连板/一字/接近涨停、龙虎榜；写入运行记录
- 规则：一进二（承接现有规则与 2026-07-21 设计）+ 板块轮动/主线分 + 生命周期与四维强度
- API：在 `/api/v1/short-term` 上补齐 refresh / overview / candidates / sectors，并增加题材生命周期轨迹接口；题材 list/detail/ranking 附带当日阶段与强度
- 前端：短线雷达区块按 2026-07-21 设计补齐；`ThemeCard` / 题材库阶段列与强度；详情强度仪表 + 轨迹；热门区紧凑布局；题材库阶段筛选
- 测试：采集解析、规则、API、关键组件与看板集成

### 本次不包含

- 主线 vs 支线叙事图升级（后续 P2）
- 催化雷达分类「新催化 / 旧闻复读」（后续 P3）
- 自选题材工作台（后续 P4）
- 复盘模式、AI 题材日报（后续 P5）
- 题材挖掘 B：低位分支 / 补涨 / 隐性龙头（后续 P1）
- 自动交易、收益承诺、全局无用户 Key 的 LLM 日报
- 流式推送日内 tick（本版以交易日快照为主；盘中可重复 refresh 覆盖当日）

## 与已有文档关系

- **扩展并落地** `2026-07-21-short-term-opportunity-radar-design.md`，不另起冲突口径。
- 在 `sector_rotation_snapshots` 上增加生命周期与四维强度字段（见下文）。
- 现有 `MarketStrategyCard` / `BoardUpgradeReference` **保留入口**，数据源改为读新表；交互不无故删除。
- 一进二硬性排除 / 加分 / 降权沿用现有 `short_term_rules` 与 2026-07-21 规则描述。

## 总体架构

```text
POST /short-term/signals/refresh
        │
        ▼
short_term_signal_runs 开始
        │
        ├─ ShortTermScraper → daily_stock_signals
        ├─ DragonTigerScraper → dragon_tiger_entries
        ├─（复用）行情刷新 → theme_market_snapshots / themes 报价
        ├─ SectorRotationService → sector_rotation_snapshots
        │         （生命周期 + 四维强度 + mainline/risk）
        └─ RuleEngine / FirstToSecond → short_term_candidates
        │
        ▼
run: success | partial | failed + source_status
        │
        ▼
GET overview / sectors / candidates / lifecycle
GET themes*（join 最近交易日阶段与强度）
        │
        ▼
看板雷达 UI + ThemeCard/题材库 + 详情仪表与轨迹
```

原则：

- 采集与规则解耦；源失败只影响对应指标，不阻断其它写入。
- 同一 `trade_date` 重复刷新幂等覆盖。
- 非交易日默认落到最近有信号或有快照的交易日，响应标注实际 `trade_date`。

## 数据模型

### `daily_stock_signals`

| 字段 | 说明 |
|------|------|
| `id` | 自增主键 |
| `trade_date` | 交易日 |
| `stock_id` | 股票外键 |
| `theme_id` | 主关联题材，可空（多题材时取热度/涨幅最高者） |
| `signal_type` | `limit_up` / `first_limit_up` / `second_limit_up` / `failed_limit_up` / `one_word_limit_up` / `near_limit_up` / `abnormal_move` |
| `limit_up_order` | 同日上板顺序，可空 |
| `first_limit_up_at` / `last_limit_up_at` | 首次/最后封板时间 |
| `open_board_count` | 开板次数 |
| `streak_days` | 连板天数 |
| `is_one_word` / `is_failed` | 一字 / 炸板 |
| `price`, `turnover_rate`, `amount`, `market_cap`, `float_market_cap` | 行情摘要 |
| `source`, `source_payload` | 来源与原始摘要 JSON |
| `created_at` / `updated_at` | 时间戳 |

索引：`(trade_date, signal_type)`、`(trade_date, stock_id)`、`(trade_date, theme_id)`。  
幂等：同一 `(trade_date, stock_id, signal_type)` upsert。

### `dragon_tiger_entries`

| 字段 | 说明 |
|------|------|
| `id`, `trade_date`, `stock_id` | 主键与关联 |
| `reason` | 上榜原因 |
| `buy_amount` / `sell_amount` / `net_amount` | 买卖与净额 |
| `seat_summary` | 席位摘要 |
| `source`, `source_payload` | 来源 |
| `created_at` / `updated_at` | 时间戳 |

索引：`(trade_date, stock_id)`、`(trade_date, net_amount)`。  
幂等：`(trade_date, stock_id, reason)` upsert。

### `sector_rotation_snapshots`

保留 2026-07-21 字段，并新增生命周期与强度：

| 字段 | 说明 |
|------|------|
| `trend_score`, `emotion_score`, `rotation_score`, `mainline_score`, `risk_score` | 轮动与主线分 |
| `strong_stock_count`, `limit_up_count`, `failed_limit_up_count`, `near_limit_up_count` | 聚合计数 |
| `latest_catalyst_at`, `summary`, `source` | 催化时间与摘要 |
| **`lifecycle_stage`** | `germination` / `fermentation` / `climax` / `divergence` / `ebb` |
| **`lifecycle_confidence`** | 0–100 |
| **`strength_score`** | 0–100，四维加权总分 |
| **`limit_quality_score`** | 涨停质量 0–100 |
| **`flow_score`** | 回流 0–100；源缺失时可空 |
| **`leader_clarity_score`** | 辨识度龙头 0–100 |
| **`breadth_score`** | 跟风宽度 0–100 |
| **`score_breakdown`** | JSON：分项、命中规则、降级原因 |
| **`degraded`** | bool |
| **`missing_metrics`** | JSON 数组，如 `["flow"]` |

唯一索引：`(trade_date, theme_id)`。

覆盖范围：当日热度 Top 100 与涨幅 Top 100 的并集，再加上有涨停信号命中的题材（常量可配置，默认 100）。

### `short_term_signal_runs`

| 字段 | 说明 |
|------|------|
| `id`, `trade_date` | |
| `status` | `success` / `partial` / `failed` |
| `started_at` / `finished_at` | |
| `source_status` | JSON：各源 success/error |
| `error_message` | 可空 |
| `created_at` / `updated_at` | |

### `short_term_candidates`

与 2026-07-21 一致：`strategy`（首版 `first_to_second`）、`score` / `rank` / `decision`、`matched_rules` / `excluded_rules` / `risk_flags`、展望与建议文案等。  
幂等倾向：`(trade_date, strategy, stock_id)` upsert。

### 与现有表关系

- **不改** `theme_market_snapshots` 结构；广度统计继续由行情刷新写入；短线规则读取上涨家数等作为辅助输入。
- `themes.heat_index` / `rise_fall_pct` 仍由现有报价任务更新；轮动计算时读取。
- 题材列表/详情 API 附带当日（或最近交易日）`lifecycle_stage` + `strength_score`（join 快照）。

### 阶段枚举与中文

| 存库 | UI |
|------|-----|
| `germination` | 萌芽 |
| `fermentation` | 发酵 |
| `climax` | 高潮 |
| `divergence` | 分歧 |
| `ebb` | 退潮 |

## 生命周期与四维强度规则

输入按题材、交易日 T：

| 来源 | 用途 |
|------|------|
| `daily_stock_signals`（T，成分交集） | 涨停/炸板/一字/连板 |
| `dragon_tiger_entries`（T，成分交集） | 回流 |
| `theme_market_snapshots`（T 与近 10 日） | 涨停家数、涨跌家数、题材涨跌幅 |
| `themes` | `heat_index`、`stock_count` |
| 成分股当日 `rise_fall_pct` | 龙头领先、宽度 |

窗口默认：**近 10 个有快照的交易日**；不足则用已有天数并降低 `lifecycle_confidence`。

### 涨停质量 `limit_quality_score`

- 封板率 = 成功涨停数 / (成功数 + 炸板数)
- 基础分 = 封板率 × 80
- 连板（`streak_days ≥ 2`）家数占比加分，最多 +15
- 一字板占比过高（>50% 且涨停≥2）减分，最多 −20
- 当日无涨停也无炸板：记 25 分并在 breakdown 标明「无板观察」，置信偏低

### 回流 `flow_score`

- 成分股龙虎榜 `net_amount` 合计，按当日题材净额分位映射 0–100
- 龙虎榜源失败或该题材无上榜股：`flow_score = null`，`missing_metrics` 含 `"flow"`，`degraded = true`

### 辨识度龙头 `leader_clarity_score`

- 题材内涨幅最高股（优先涨停股）相对题材均涨的领先幅度；第二名落后明显则高分；群龙无首则低分
- 无有效行情：中性 40 并标记低置信

### 跟风宽度 `breadth_score`

- 0.5 × (上涨家数 / 有效交易家数) + 0.5 × min(涨停家数 / max(stock_count×0.08, 1), 1)，映射 0–100
- 停牌过多时分母用非停牌家数

### 总分 `strength_score`

- 有回流：质量 30% + 回流 25% + 龙头 25% + 宽度 20%
- 无回流：质量 35% + 龙头 35% + 宽度 30%（不把回流当 0 分瞒报）

### 生命周期 `lifecycle_stage`

优先级从上到下，先命中先定：

| 阶段 | 判定要点 |
|------|----------|
| 高潮 `climax` | 近 3 日涨停家数处于窗口高位，且 `strength_score ≥ 70`，题材涨幅仍强 |
| 分歧 `divergence` | 近高位曾高潮或发酵，但当日炸板↑或涨停家数↓≥30%；或质量分↓而热度仍高 |
| 退潮 `ebb` | 近 3 日涨停家数与热度双降，`strength_score < 40`，上涨占比弱 |
| 发酵 `fermentation` | 近 3–5 日涨停或热度斜率明显为正，宽度改善，未达高潮 |
| 萌芽 `germination` | 其余弱信号或零星涨停 |

`lifecycle_confidence` 由窗口天数、信号覆盖率、是否缺回流共同决定。  
`score_breakdown` 至少含：`stage_reason`、`inputs`、`weights`、`missing_metrics`。

### 其它轮动字段

- `mainline_score`：偏 `strength_score` + 热度分位 + 是否高潮/发酵
- `risk_score`：炸板率、退潮/分歧、龙虎净卖
- 计数类字段直接聚合信号表
- `summary`：一句中文规则模板（非 LLM）

## 服务拆分

| 模块 | 职责 |
|------|------|
| `scrapers/short_term_signals.py` | 拉解析涨停池等，不写业务分 |
| `scrapers/dragon_tiger.py` | 龙虎榜 |
| `repositories/short_term_signal.py` | 五表 upsert / 按日查询 |
| `services/sector_rotation.py` | 轮动分 + 生命周期/四维 |
| `services/short_term_rules.py` | 一进二规则（增强为读信号表） |
| `services/short_term.py` | 编排 refresh、组装 overview/sectors |
| `services/first_to_second.py` | 优先读 `short_term_candidates`；无行时可降级现算并标 `degraded` |

## API 设计

前缀：`/api/v1/short-term`

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/signals/refresh` | 全量采集+规则；`trade_date?`；需登录 |
| `GET` | `/overview` | 展望、情绪、主线摘要、风险、策略卡；优先读库；可匿名 |
| `POST` | `/overview/refresh-data` | 兼容现入口：内部转调 signals refresh + 返回 overview |
| `POST` | `/overview/analyze` | 不拉外网，仅用库内数据重算 |
| `GET` | `/candidates` | `strategy=first_to_second`；读候选表 |
| `GET` | `/sectors` | 主线/强势/异动，含 `lifecycle_stage`、`strength_score` |
| `GET` | `/themes/{theme_id}/lifecycle` | 近 `days`（默认 10）轨迹 |

题材只读扩展：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/themes`、`/themes/ranking`、`/themes/{id}` | 增加可选 `lifecycle_stage`、`strength_score`、`lifecycle_confidence` |

降级约定：读接口统一可带 `degraded`、`missing_sources`、实际 `trade_date`。缺龙虎榜时仍返回阶段与其它三维，`flow_score` 为 null。

兼容：保留现有 first-to-second 与 overview 主字段；扩展字段不删旧字段。

## 前端设计

### 看板 `/`

- 新增短线机会雷达区块（策略卡上方或紧邻）：
  - `ShortTermRadarSection`
  - `ShortTermOverviewPanel`
  - `SectorRotationPanel`（主线带阶段徽章 + 强度分）
  - 一进二继续用 `BoardUpgradeReference`（或表格式候选）
- 保留 `MarketStrategyCard`，数据来自库内 overview
- `ThemeCard`：阶段徽章 + 强度分；布局更紧凑
- `ThemeRiseFallBar`：高度略减；阶段色点可选（拥挤则省略）
- Nav「题材看板」可加锚点「短线雷达」

### 题材库 `/themes`

- 列表增加只读列：阶段、强度（无快照显示 —）
- 支持按阶段筛选

### 题材详情 `/themes/:id`

- 生命周期徽章 + 置信度
- 四维强度仪表；回流缺失显示「暂缺」
- 近 10 日轨迹：阶段色带 + 强度折线（接 lifecycle API）
- 空态引导至看板刷新短线数据

### 文案与体验

- 阶段/分数 tooltip（`stage_reason` 或固定说明）
- 雷达区脚注：短线观察工具，非投资建议
- 加载/失败与现有 Toast、中文错误一致

## 测试策略

后端：

- 模型与迁移：表、索引、字段类型
- 采集解析：涨停、炸板、一字、龙虎榜 fixture
- 规则：四维、五阶段主路径；缺回流权重重分配；一进二硬性排除/加分/降权
- API：正常、partial、无交易日、lifecycle 空历史

前端：

- API client：参数、降级字段
- 徽章、仪表、轨迹空态、雷达刷新状态
- 看板：雷达渲染、题材卡紧凑与阶段
- 题材库阶段列与筛选
- 详情仪表与轨迹

## 风险与降级

- 数据源字段不稳定：保留 `source_payload`，缺字段写入 run
- 龙虎榜或上板时间缺失：相关规则/回流降级，界面明示
- 非交易日：使用最近有效交易日并标注
- 大量抓取失败：partial + missing_sources，不生成伪结论
- 计算成本：Top N + 有信号题材，避免全库空转
- 实现体量大：按「迁移 → 采集 → 规则落库 → API → 看板雷达 → 卡片/库/详情」切片提交，**不砍本设计范围**

## 验收标准

1. 迁移后五表存在且索引正确。
2. 登录用户可 refresh；库中有当日信号；龙虎失败时 run=`partial` 且 overview `degraded`。
3. overview / sectors / candidates / lifecycle 可用；题材 list/detail/ranking 带阶段与强度。
4. 看板可见完整雷达 UI + 题材卡阶段/强度；详情可见四维仪表 + 10 日轨迹；题材库可见阶段列与筛选。
5. 生命周期与四维规则有单元测试覆盖主路径与缺回流。
6. 不编造回流/封板；缺数据明示。
7. 现有一进二、策略卡入口保留；响应兼容旧字段。

## 后续路线（本设计不实现）

1. **P1 题材挖掘 B**：低位分支、补涨、隐性龙头（消费本版阶段与强度）
2. **P2 主线 vs 支线叙事图**
3. **P3 催化雷达**（新催化 / 旧闻复读）
4. **P4 自选题材工作台**
5. **P5 复盘模式 + 可选 AI 题材日报**
