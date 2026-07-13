/** 链路点卡片组件
 *
 * 显示产业链环节信息，可展开查看关联股票。
 * 使用 TanStack Query 获取关联股票数据。
 */

import { useState, memo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronUp, Building, AlertCircle } from 'lucide-react'
import { StockList } from '@/components/StockList'
import { StockListSkeleton } from '@/components/StockListSkeleton'
import { fetchThemeStocks } from '@/api/theme'
import type { IndustryChainBrief } from '@/types/theme'

interface ChainPointCardProps {
  chainPoint: IndustryChainBrief
  themeId: number
}

/** 解析代表公司列表 */
function parseRepresentativeCompanies(
  companies: string[] | Record<string, unknown> | null
): string[] {
  if (!companies) return []
  if (Array.isArray(companies)) return companies as string[]
  return Object.values(companies) as string[]
}

export const ChainPointCard = memo(function ChainPointCard({ chainPoint, themeId }: ChainPointCardProps) {
  const [expanded, setExpanded] = useState(false)

  // 获取关联股票数据
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['theme-stocks', themeId, chainPoint.level],
    queryFn: () => fetchThemeStocks(themeId, chainPoint.level),
    enabled: expanded,
    staleTime: 5 * 60 * 1000,
  })

  const stocks = data?.items ?? []
  const companies = parseRepresentativeCompanies(chainPoint.representative_companies)

  return (
    <div className="rounded-lg border border-border bg-card p-3 transition-colors hover:border-primary/20">
      {/* 头部：名称和展开按钮 */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-foreground truncate">
            {chainPoint.name}
          </h4>
          {chainPoint.description && (
            <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
              {chainPoint.description}
            </p>
          )}
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="shrink-0 rounded-md p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          aria-label={expanded ? '折叠' : '展开'}
        >
          {expanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* 代表公司 */}
      {companies.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {companies.map((company, index) => (
            <span
              key={index}
              className="inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground"
            >
              <Building className="h-3 w-3" />
              {company}
            </span>
          ))}
        </div>
      )}

      {/* 展开的股票列表 */}
      {expanded && (
        <div className="mt-3 border-t border-border pt-3">
          {isLoading && <StockListSkeleton />}
          {isError && (
            <div className="flex items-center gap-2 py-2 text-xs text-destructive">
              <AlertCircle className="h-3.5 w-3.5" />
              <span>加载失败：{error?.message ?? '未知错误'}</span>
            </div>
          )}
          {!isLoading && !isError && <StockList stocks={stocks} />}
        </div>
      )}
    </div>
  )
})
