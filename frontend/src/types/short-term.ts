export type MarketStrength = 'strong' | 'weak'
export type ShortTermPeriod = 'today' | 'current_week' | 'half_month' | 'current_month' | 'custom'
export type ShortTermPeriodStatusType = 'progress' | 'success' | 'error'
export type StrategyCardDataSource = 'database' | 'live'

export interface ShortTermPeriodStatus {
  type: ShortTermPeriodStatusType
  message: string
}

export interface MarketStrategyCardResponse {
  title: string
  index_strength: MarketStrength
  emotion_strength: MarketStrength
  primary_strategy: string
  secondary_strategy: string
  operation_advice: string
  focus_targets: string[]
  rationale: string[]
  /** 与 rationale 一一对应的计算公式说明 */
  formulas?: string[]
}

export interface RefreshMeta {
  elapsed_ms: number
  quote_source: string
  quote_attempts: string[]
  quote_message?: string
}

export interface ShortTermOverviewResponse {
  trade_date: string
  period: ShortTermPeriod
  period_label: string
  start_date: string
  end_date: string
  degraded: boolean
  missing_sources: string[]
  market_emotion: string
  short_term_outlook: string
  operation_advice: string
  tracking_focus: string[]
  core_conclusion: string
  risk_signals: string[]
  sector_count: number
  candidate_count: number
  strategy_card: MarketStrategyCardResponse
  refresh_meta?: RefreshMeta | null
}

export type FirstToSecondDecision = 'candidate' | 'watch' | 'excluded'

export interface FirstToSecondCandidateItem {
  code: string
  name: string
  theme_name: string | null
  price: number | null
  market_cap: number | null
  float_market_cap: number | null
  turnover_rate: number | null
  amount: number | null
  first_limit_up_at: string | null
  open_board_count: number
  score: number
  decision: FirstToSecondDecision
  matched_rules: string[]
  excluded_rules: string[]
  risk_flags: string[]
  catalysts: string[]
  operation_advice: string
  core_conclusion: string
}

export interface FirstToSecondCandidateResponse {
  trade_date: string
  previous_trade_date: string
  refreshed_at: string
  degraded: boolean
  missing_sources: string[]
  candidates: FirstToSecondCandidateItem[]
  excluded_count: number
  source_status: Record<string, string>
}

export type LifecycleStage =
  | 'germination'
  | 'fermentation'
  | 'climax'
  | 'divergence'
  | 'ebb'

export const LIFECYCLE_STAGE_LABEL: Record<LifecycleStage, string> = {
  germination: '萌芽',
  fermentation: '发酵',
  climax: '高潮',
  divergence: '分歧',
  ebb: '退潮',
}

export interface ShortTermSignalRefreshResponse {
  trade_date: string
  status: 'success' | 'partial' | 'failed'
  signal_count: number
  dragon_tiger_count: number
  sector_count: number
  candidate_count: number
  degraded: boolean
  missing_sources: string[]
  source_status: Record<string, unknown>
  error_message: string | null
}

export interface SectorRotationItem {
  theme_id: number
  theme_name: string
  /** theme=普通题材, market=市场表现, indicator=行情指标 */
  board_kind: 'theme' | 'market' | 'indicator'
  lifecycle_stage: LifecycleStage
  lifecycle_confidence: number
  strength_score: number
  mainline_score: number
  risk_score: number
  limit_up_count: number
  failed_limit_up_count: number
  summary: string
  degraded: boolean
  missing_metrics: string[]
}

export interface SectorRotationResponse {
  trade_date: string
  items: SectorRotationItem[]
  degraded: boolean
  missing_sources: string[]
}

export interface LifecyclePoint {
  trade_date: string
  lifecycle_stage: LifecycleStage
  strength_score: number
  limit_quality_score: number | null
  flow_score: number | null
  leader_clarity_score: number | null
  breadth_score: number | null
  lifecycle_confidence: number
}

export interface ThemeLifecycleResponse {
  theme_id: number
  days: number
  points: LifecyclePoint[]
  degraded: boolean
  missing_sources: string[]
}
