/** 个股 AI 研判报告 API */

import { apiClient } from '@/api/client'
import type { StockAiReport } from '@/types/stock-ai-report'

export async function fetchStockAiReport(code: string): Promise<StockAiReport> {
  const { data } = await apiClient.get<StockAiReport>(`/stocks/${code}/ai-report`)
  return data
}

export async function generateStockAiReport(
  code: string,
  options: { force?: boolean } = {}
): Promise<StockAiReport> {
  const { data } = await apiClient.post<StockAiReport>(
    `/stocks/${code}/ai-report`,
    { force: Boolean(options.force) },
    { timeout: 300_000 }
  )
  return data
}
