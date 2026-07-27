/** 题材全部成分股区域 */

import { useQuery } from '@tanstack/react-query'
import { AlertCircle } from 'lucide-react'
import { fetchThemeStocks } from '@/api/theme'
import { StockList } from '@/components/StockList'
import { StockListSkeleton } from '@/components/StockListSkeleton'

interface ThemeConstituentStocksProps {
  themeId: number
}

export function ThemeConstituentStocks({ themeId }: ThemeConstituentStocksProps) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['theme-stocks', themeId, 'all'],
    queryFn: () => fetchThemeStocks(themeId, undefined, 1, 100),
    staleTime: 5 * 60 * 1000,
  })

  const stocks = data?.items ?? []

  return (
    <section>
      <div className="mb-4 flex items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-foreground">全部成分股</h2>
        {!isLoading && !isError && (
          <span className="text-sm text-muted-foreground">共 {data?.total ?? 0} 只</span>
        )}
      </div>

      {isLoading && <StockListSkeleton layout="grid" />}

      {isError && (
        <div className="flex items-center gap-2 py-4 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          <span>成分股加载失败：{error?.message ?? '未知错误'}</span>
        </div>
      )}

      {!isLoading && !isError && stocks.length === 0 && (
        <div className="border-y border-dashed border-border py-8 text-center text-sm text-muted-foreground">
          暂无成分股数据
        </div>
      )}

      {!isLoading && !isError && stocks.length > 0 && (
        <StockList stocks={stocks} layout="grid" />
      )}
    </section>
  )
}
