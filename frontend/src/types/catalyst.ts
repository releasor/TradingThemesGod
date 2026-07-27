/** 催化雷达 API 类型 */

export type CatalystFreshness = 'new' | 'replay' | 'unknown'
export type CatalystActorType = 'policy' | 'company' | 'other' | 'unknown'

export interface CatalystFeedItem {
  event_id: number
  theme_id: number
  theme_name: string
  title: string
  summary: string
  source: string
  url: string
  published_at: string
  relevance_score: number
  freshness: string
  actor_type: string
  classified_by: string | null
}

export interface CatalystFeedResponse {
  items: CatalystFeedItem[]
  total: number | null
}

export interface NewsHeadlineItem {
  title: string
  url: string
  published_at: string
  match_note: string
}

export interface CatalystThemeSummaryResponse {
  theme_id: number
  theme_name: string
  lifecycle_stage: string | null
  strength_score: number | null
  counts: Record<string, number>
  recent_events: CatalystFeedItem[]
  news_headlines: NewsHeadlineItem[]
}

export interface CatalystEnsureResponse {
  classified_rules: number
  model_queued: boolean
}

export interface CatalystFeedParams {
  freshness?: string
  actor_type?: string
  theme_id?: number
  q?: string
  from?: string
  to?: string
  limit?: number
  offset?: number
}

export interface CatalystEnsureParams {
  days?: number
  use_model?: boolean
}
