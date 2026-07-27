/** 题材挖掘 API 类型 */

export type MiningType = 'low_branch' | 'catch_up' | 'hidden_leader'

export type MiningNoteStatus = 'pending' | 'running' | 'success' | 'failed'

export interface MiningMemberItem {
  stock_id: number
  stock_code: string | null
  stock_name: string | null
  concept_node_id: number | null
  concept_node_name: string | null
  score: number
  rank: number
  role_tag: string
  metrics: Record<string, unknown>
  rise_fall_pct: number | null
}

export interface MiningNoteResponse {
  id: number
  card_id: number
  user_id: number
  status: string
  content_md: string
  model_name: string | null
  error: string | null
}

export interface MiningCardItem {
  id: number
  trade_date: string
  theme_id: number
  theme_name: string
  mining_type: string
  score: number
  rank: number
  lifecycle_stage: string
  strength_score: number
  rationale: string
  score_breakdown: Record<string, unknown>
  degraded: boolean
  missing_metrics: unknown[]
  member_count: number
  members: MiningMemberItem[]
  note: MiningNoteResponse | null
}

export interface MiningBoardResponse {
  trade_date: string
  low_branch: MiningCardItem[]
  catch_up: MiningCardItem[]
  hidden_leader: MiningCardItem[]
}

export interface MiningEnsureResponse {
  trade_date: string
  theme_count: number
  card_count: number
  counts: Record<string, number>
}

export interface MiningBoardParams {
  trade_date?: string
}

export interface MiningEnsureParams {
  trade_date?: string
}
