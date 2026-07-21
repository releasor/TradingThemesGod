# 短线机会雷达完整数据链路设计

## 背景

看板需要在现有题材热度与新闻展示之外，新增一个面向短线交易复盘和次日筛选的“短线机会雷达”。它要根据前日趋势、市场情绪、板块轮动、主线题材与强势股、龙虎榜核心动向、最新新闻时间催化、风险信号、异动股票、今日接近异动股票等信息，输出短期展望、操作建议、重点跟踪对象和核心结论，并基于昨天首板筛选今天一进二候选。

现有系统已经有题材、股票、题材成分股、新闻、题材驱动事件和市场快照，但缺少每日涨停/炸板/一字/上板时间、龙虎榜、流通市值、成交流动性、短线候选结果等结构化数据。因此本功能必须新增独立数据链路，避免用不完整字段生成不可验证结论。

## 目标

- 看板热门题材 Top 20 区域变小，题材卡片变紧凑，提升信息密度。
- 新增短线行情采集链路，采集每日涨停、炸板、连板、一字板、接近异动、龙虎榜、个股行情快照和新闻催化。
- 新增短线规则引擎，按用户给出的硬性排除条件、加分条件和降权条件生成可解释候选结果。
- 新增 REST API 返回短线概览、板块轮动、风险信号和一进二候选。
- 前端新增“短线机会雷达”模块，展示短期展望、操作建议、重点跟踪对象、核心结论、候选股票与排除原因。
- 数据源失败时必须明确标记降级状态，不得伪造结论。

## 非目标

- 不提供自动交易、下单或仓位执行。
- 不承诺筛选结果具备投资收益，只提供基于已采集数据的规则化观察。
- 不把短线结果写回 `themes` 作为永久题材属性。
- 不删除现有题材、新闻或图谱功能。

## 数据源策略

新增短线数据采集器，默认使用公开数据源，结构上允许后续接入 Tushare 等增强源。

默认采集内容：

- 涨停池、炸板池、连板池、一字板、首次封板时间、最终封板时间、开板次数。
- 个股行情快照：价格、涨跌幅、成交额、换手率、总市值、流通市值。
- 龙虎榜：上榜原因、买入额、卖出额、净买额、席位摘要。
- 新闻催化：复用现有新闻和题材驱动事件，新增短线催化分类。
- 板块行情：题材涨跌幅、热度、成分股涨跌分布、强势股数量。

采集器必须记录每个数据源的成功、失败、缺字段和降级原因。字段缺失时只影响相关规则，不影响其它可验证规则运行。

## 数据模型

新增 Alembic 迁移，表命名和索引遵循项目 MySQL 约定。

### `daily_stock_signals`

每日个股短线信号。

- `id`: 自增主键
- `trade_date`: 交易日
- `stock_id`: 股票 ID
- `theme_id`: 主要关联题材 ID，可为空
- `signal_type`: `limit_up`, `first_limit_up`, `second_limit_up`, `failed_limit_up`, `one_word_limit_up`, `near_limit_up`, `abnormal_move`
- `limit_up_order`: 同日上板顺序，可为空
- `first_limit_up_at`: 首次封板时间，可为空
- `last_limit_up_at`: 最后封板时间，可为空
- `open_board_count`: 开板次数
- `streak_days`: 连板天数
- `is_one_word`: 是否一字板
- `is_failed`: 是否炸板
- `price`: 收盘价或最新价
- `turnover_rate`: 换手率
- `amount`: 成交额
- `market_cap`: 总市值
- `float_market_cap`: 流通市值
- `source`: 数据源
- `source_payload`: JSON 原始摘要
- `created_at`, `updated_at`

索引：

- `idx_daily_stock_signals_date_type`
- `idx_daily_stock_signals_date_stock`
- `idx_daily_stock_signals_date_theme`

### `dragon_tiger_entries`

龙虎榜明细。

- `id`
- `trade_date`
- `stock_id`
- `reason`
- `buy_amount`
- `sell_amount`
- `net_amount`
- `seat_summary`
- `source`
- `source_payload`
- `created_at`, `updated_at`

索引：

- `idx_dragon_tiger_entries_date_stock`
- `idx_dragon_tiger_entries_date_net`

### `sector_rotation_snapshots`

板块轮动快照。

- `id`
- `trade_date`
- `theme_id`
- `trend_score`
- `emotion_score`
- `rotation_score`
- `mainline_score`
- `risk_score`
- `strong_stock_count`
- `limit_up_count`
- `failed_limit_up_count`
- `near_limit_up_count`
- `latest_catalyst_at`
- `summary`
- `source`
- `created_at`, `updated_at`

索引：

- `idx_sector_rotation_snapshots_date_theme`
- `idx_sector_rotation_snapshots_date_mainline`

### `short_term_signal_runs`

每次短线刷新运行记录。

- `id`
- `trade_date`
- `status`: `success`, `partial`, `failed`
- `started_at`
- `finished_at`
- `source_status`: JSON，记录各来源状态
- `error_message`
- `created_at`, `updated_at`

索引：

- `idx_short_term_signal_runs_date_status`

### `short_term_candidates`

规则引擎输出。

- `id`
- `trade_date`
- `strategy`: 当前为 `first_to_second`
- `stock_id`
- `theme_id`
- `score`
- `rank`
- `decision`: `candidate`, `excluded`, `watch`
- `matched_rules`: JSON
- `excluded_rules`: JSON
- `risk_flags`: JSON
- `outlook`
- `operation_advice`
- `tracking_focus`
- `core_conclusion`
- `created_at`, `updated_at`

索引：

- `idx_short_term_candidates_date_strategy_rank`
- `idx_short_term_candidates_date_stock`
- `idx_short_term_candidates_date_theme`

## 筛选规则

规则引擎分为硬性排除、加分、降权三类，并保留每条规则命中说明。

硬性排除：

- 流通市值 `<10亿` 排除。
- 流通市值 `>100亿` 排除。
- 价格 `>25元` 排除。
- 流动性差排除，默认以成交额和换手率同时过低判断。
- 昨日首板炸板排除。
- 昨日首板一字板排除。
- 直线、小题材首板排除。

优先候选：

- 政策利好。
- 行业催化。
- 突发事件驱动。
- 主流题材。
- 题材越新、想象空间越大，优先级越高。
- 流通市值 `20-80亿` 加分。
- 总市值 `50-150亿` 加分。
- 同一题材多个首板时，选择先上板的股票优先。

降权：

- 老题材或反复炒作题材。
- 缺少新闻催化。
- 龙虎榜净卖出明显。
- 板块情绪退潮。
- 风险信号集中。

## 后端服务

新增模块：

- `app/models/short_term_signal.py`
- `app/schemas/short_term.py`
- `app/repositories/short_term.py`
- `app/services/short_term.py`
- `app/services/short_term_rules.py`
- `app/scrapers/short_term.py`
- `app/api/short_term.py`

服务职责：

- 采集器只负责拉取和解析源数据。
- Repository 负责幂等写入、按交易日查询、批量更新。
- Rule service 负责筛选、评分、输出解释。
- API service 负责组装短线概览、候选列表、板块轮动、风险信号。

## API 设计

新增路由前缀：`/api/v1/short-term`

- `POST /signals/refresh?trade_date=YYYY-MM-DD`
  - 拉取短线数据并运行规则引擎。
  - 返回运行状态、成功来源、失败来源、生成候选数量。
- `GET /overview?trade_date=YYYY-MM-DD`
  - 返回短期展望、市场情绪、板块轮动、风险信号、核心结论。
- `GET /candidates?trade_date=YYYY-MM-DD&strategy=first_to_second`
  - 返回一进二候选和排除原因。
- `GET /sectors?trade_date=YYYY-MM-DD`
  - 返回主线题材、强势股、异动股票、接近异动股票。

所有接口必须使用统一中文错误提示，数据不足时返回 `degraded: true` 和 `missing_sources`，而不是 500。

## 前端设计

看板新增“短线机会雷达”区块，位置在主内容上方或热门题材前方，保持工具型高密度风格。

组件拆分：

- `ShortTermRadarSection`: 总入口。
- `ShortTermOverviewPanel`: 短期展望、操作建议、核心结论。
- `SectorRotationPanel`: 板块轮动、市场情绪、风险信号。
- `FirstToSecondCandidatesTable`: 昨日首板到今日一进二候选。
- `ShortTermRuleBadges`: 命中规则、排除规则、风险标签。

热门题材 Top 20 调整：

- `ThemeRiseFallBar` 高度从 520px 调小，柱体和标签更紧凑。
- `ThemeCard` padding、间距、字号调小。
- 热门题材网格在宽屏增加列数，减少单张卡片占用面积。

## 测试策略

后端：

- 模型和迁移测试：验证表、索引、字段类型。
- 采集解析单元测试：用固定 fixture 覆盖涨停、炸板、一字、龙虎榜。
- 规则引擎测试：覆盖硬性排除、加分、降权、同题材按上板时间排序。
- API 测试：覆盖正常、部分数据缺失、无交易日数据。

前端：

- API client 测试：参数、响应转换、降级状态。
- 组件测试：候选表、规则标签、空状态、降级提示。
- 看板测试：短线雷达渲染、热门题材紧凑布局。

## 风险与降级

- 数据源字段不稳定：采集器保留 source payload 摘要，并将缺字段写入运行记录。
- 龙虎榜或上板时间缺失：相关规则降级，不参与总分，但界面显示缺失。
- 非交易日：默认使用最近一个有数据的交易日，并在界面标注。
- 大量抓取失败：API 返回部分结果和失败来源，前端显示“数据不完整”。
- 规则误伤：所有候选必须展示命中和排除原因，便于人工判断。

## 验收标准

- 用户能在看板看到更紧凑的热门题材 Top 20 和题材卡片。
- 用户能刷新短线信号并看到运行状态。
- 用户能查看短线概览、主线板块、风险信号、重点跟踪对象和核心结论。
- 用户能查看昨日首板到今日一进二候选，并看到每只股票的命中规则、排除规则、分数和操作建议。
- 数据源缺失时界面明确提示降级，不生成伪结论。
