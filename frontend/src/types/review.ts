/** 复盘台 API 类型 */

export interface ReviewRunBrief {
  id: number
  trade_date: string
  run_type: string
  status: string
  source_status: Record<string, unknown>
  started_at: string | null
  finished_at: string | null
}

export interface ReviewCandidateItem {
  stock_id: number
  stock_code: string | null
  stock_name: string | null
  theme_id: number | null
  theme_name: string | null
  strategy: string
  score: number
  rank: number
  decision: string
}

export interface ReviewStageTransition {
  theme_id: number
  theme_name: string | null
  from_stage: string | null
  to_stage: string
  strength_score: number | null
}

export interface ReviewCandidatePerformance {
  stock_id: number
  stock_code: string | null
  stock_name: string | null
  same_day_pct: number | null
  next_day_pct: number | null
  reason: string | null
}

export interface ReviewPerformance {
  candidates: ReviewCandidatePerformance[]
}

export interface ReviewThemeDayPoint {
  trade_date: string
  stage: string
  strength_score: number
  rise_fall_pct: number | null
}

export interface ReviewDayResponse {
  trade_date: string
  degraded: boolean
  missing_sources: string[]
  runs: ReviewRunBrief[]
  strategy_card: Record<string, unknown> | null
  candidates: ReviewCandidateItem[]
  stage_transitions: ReviewStageTransition[]
  performance: ReviewPerformance | null
  report_summary: string | null
}

export interface ReviewThemeResponse {
  theme_id: number
  theme_name: string
  days: number
  trajectory: ReviewThemeDayPoint[]
  related_candidates: ReviewCandidateItem[]
  run_refs: ReviewRunBrief[]
}

export interface ReviewDayListResponse {
  items: string[]
}

export interface ReviewAiReportResponse {
  trade_date: string
  user_id: number | null
  status: string
  content_md: string
  content_json: Record<string, unknown>
  model_name: string | null
  error: string | null
  source_run_ids: unknown[]
}
