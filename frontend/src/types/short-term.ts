export type MarketStrength = 'strong' | 'weak'
export type ShortTermPeriod = 'today' | 'current_week' | 'half_month' | 'current_month' | 'custom'
export type ShortTermPeriodStatusType = 'progress' | 'success' | 'error'

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
