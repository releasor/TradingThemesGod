"""短线机会雷达 API 模型。"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

ShortTermPeriod = Literal[
    "today", "current_week", "half_month", "current_month", "custom"
]


class MarketStrategyCardResponse(BaseModel):
    """指数与情绪组合策略卡。"""

    title: str = Field(description="卡片标题")
    index_strength: str = Field(description="指数强弱：strong/weak")
    emotion_strength: str = Field(description="情绪强弱：strong/weak")
    primary_strategy: str = Field(description="主策略")
    secondary_strategy: str = Field(description="辅助策略")
    operation_advice: str = Field(description="操作建议")
    focus_targets: list[str] = Field(default_factory=list, description="重点跟踪对象")
    rationale: list[str] = Field(default_factory=list, description="判断依据")
    formulas: list[str] = Field(
        default_factory=list, description="与判断依据一一对应的计算公式说明"
    )


class RefreshMeta(BaseModel):
    """刷新耗时与数据源信息。"""

    elapsed_ms: int = Field(default=0, description="刷新耗时（毫秒）")
    quote_source: str = Field(description="行情数据源")
    quote_attempts: list[str] = Field(default_factory=list, description="尝试过的数据源")
    quote_message: str = Field(default="", description="行情刷新说明")


class ShortTermOverviewResponse(BaseModel):
    """短线雷达概览。"""

    trade_date: date = Field(description="数据交易日")
    period: ShortTermPeriod = Field(default="today", description="统计周期")
    period_label: str = Field(default="当日", description="统计周期展示名")
    start_date: date = Field(description="统计开始日期")
    end_date: date = Field(description="统计结束日期")
    degraded: bool = Field(default=False, description="是否降级")
    missing_sources: list[str] = Field(default_factory=list, description="缺失数据源")
    market_emotion: str = Field(description="市场情绪")
    short_term_outlook: str = Field(description="短期展望")
    operation_advice: str = Field(description="操作建议")
    tracking_focus: list[str] = Field(default_factory=list, description="重点跟踪对象")
    core_conclusion: str = Field(description="核心结论")
    risk_signals: list[str] = Field(default_factory=list, description="风险信号")
    sector_count: int = Field(default=0, description="有效轮动板块数量")
    candidate_count: int = Field(default=0, description="候选数量")
    strategy_card: MarketStrategyCardResponse = Field(description="指数情绪策略卡")
    refresh_meta: RefreshMeta | None = Field(default=None, description="最近一次行情刷新元数据")


class FirstToSecondCandidateItem(BaseModel):
    """一进二候选股票。"""

    code: str = Field(description="股票代码")
    name: str = Field(description="股票名称")
    theme_name: str | None = Field(default=None, description="关联题材或行业")
    price: float | None = Field(default=None, description="最新价")
    market_cap: float | None = Field(default=None, description="总市值，单位亿元")
    float_market_cap: float | None = Field(default=None, description="流通市值，单位亿元")
    turnover_rate: float | None = Field(default=None, description="换手率")
    amount: float | None = Field(default=None, description="成交额，单位亿元")
    first_limit_up_at: str | None = Field(default=None, description="首次封板时间")
    open_board_count: int = Field(default=0, description="开板次数")
    score: int = Field(description="综合评分")
    decision: Literal["candidate", "watch", "excluded"] = Field(description="筛选结论")
    matched_rules: list[str] = Field(default_factory=list, description="命中规则")
    excluded_rules: list[str] = Field(default_factory=list, description="排除规则")
    risk_flags: list[str] = Field(default_factory=list, description="风险标签")
    catalysts: list[str] = Field(default_factory=list, description="催化说明")
    operation_advice: str = Field(description="操作建议")
    core_conclusion: str = Field(description="核心结论")


class FirstToSecondCandidateResponse(BaseModel):
    """一进二候选响应。"""

    trade_date: date = Field(description="目标交易日")
    previous_trade_date: date = Field(description="上一交易日")
    refreshed_at: str = Field(description="刷新时间")
    degraded: bool = Field(default=False, description="是否降级")
    missing_sources: list[str] = Field(default_factory=list, description="缺失数据源")
    candidates: list[FirstToSecondCandidateItem] = Field(
        default_factory=list, description="候选股票"
    )
    excluded_count: int = Field(default=0, description="排除数量")
    source_status: dict[str, str] = Field(default_factory=dict, description="数据源状态")


LifecycleStage = Literal[
    "germination", "fermentation", "climax", "divergence", "ebb"
]


class ShortTermSignalRefreshResponse(BaseModel):
    """短线信号全量刷新结果。"""

    trade_date: date
    status: Literal["success", "partial", "failed"]
    signal_count: int = 0
    dragon_tiger_count: int = 0
    sector_count: int = 0
    candidate_count: int = 0
    degraded: bool = False
    missing_sources: list[str] = Field(default_factory=list)
    source_status: dict[str, object] = Field(default_factory=dict)
    error_message: str | None = None


class SectorRotationItem(BaseModel):
    """板块轮动/主线题材项。"""

    theme_id: int
    theme_name: str
    board_kind: Literal["theme", "market", "indicator"] = Field(
        default="theme",
        description="theme=普通题材, market=市场表现, indicator=行情指标",
    )
    lifecycle_stage: LifecycleStage
    lifecycle_confidence: int = 0
    strength_score: int
    mainline_score: int
    risk_score: int = 0
    limit_up_count: int = 0
    failed_limit_up_count: int = 0
    summary: str = ""
    degraded: bool = False
    missing_metrics: list[str] = Field(default_factory=list)


class SectorRotationResponse(BaseModel):
    trade_date: date
    items: list[SectorRotationItem] = Field(default_factory=list)
    degraded: bool = False
    missing_sources: list[str] = Field(default_factory=list)


class LifecyclePoint(BaseModel):
    trade_date: date
    lifecycle_stage: LifecycleStage
    strength_score: int
    limit_quality_score: int | None = None
    flow_score: int | None = None
    leader_clarity_score: int | None = None
    breadth_score: int | None = None
    lifecycle_confidence: int = 0


class ThemeLifecycleResponse(BaseModel):
    theme_id: int
    days: int
    points: list[LifecyclePoint] = Field(default_factory=list)
    degraded: bool = False
    missing_sources: list[str] = Field(default_factory=list)
