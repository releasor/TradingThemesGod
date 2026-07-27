/** 个股 AI 研判报告类型 */

export type StockAiVerdict = 'buy' | 'watch' | 'avoid'
export type HorizonFit = 'suitable' | 'neutral' | 'unsuitable'

export interface HorizonSlot {
  fit: HorizonFit
  note: string
}

export interface StockAiReportHorizon {
  short: HorizonSlot
  swing: HorizonSlot
  medium_long: HorizonSlot
}

export interface StockAiReportSections {
  trend: string
  emotion_rotation: string
  themes_catalysts: string
  stock_position: string
  scenarios_actions: string
  risks: string
}

export interface StockAiReport {
  code: string
  stock_name: string | null
  verdict: StockAiVerdict
  horizon: StockAiReportHorizon
  confidence: number
  summary: string
  sections: StockAiReportSections
  full_report: string
  model_name: string | null
  generated_at: string
  elapsed_ms: number
  disclaimer: string
}
