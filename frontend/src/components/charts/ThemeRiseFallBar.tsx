/** 题材涨跌幅柱状图组件
 *
 * 展示 Top 10 题材的涨跌幅水平柱状图。
 */

import { memo, useMemo } from 'react'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { ThemeBrief } from '@/types/theme'
import { useChartTheme } from '@/hooks/useChartTheme'
import { RISE_FALL_COLORS } from '@/lib/chart-colors'
import { EmptyChart } from './EmptyChart'
import { cn } from '@/lib/utils'

// 注册必需的 ECharts 组件
echarts.use([BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

interface ThemeRiseFallBarProps {
  /** 题材列表（已按涨跌幅排序） */
  themes: ThemeBrief[]
  /** 自定义类名 */
  className?: string
}

/** 题材涨跌幅柱状图组件 */
export const ThemeRiseFallBar = memo(function ThemeRiseFallBar({ themes, className }: ThemeRiseFallBarProps) {
  const { colors } = useChartTheme()

  // 取 Top 10 并按涨跌幅排序
  const top10 = useMemo(
    () => [...themes].sort((a, b) => b.rise_fall_pct - a.rise_fall_pct).slice(0, 10),
    [themes],
  )

  if (top10.length === 0) {
    return <EmptyChart className={cn('h-[300px]', className)} />
  }

  const option = useMemo(() => {
    // 反转以便从上到下显示（最高在上）
    const reversed = top10.slice().reverse()
    return {
      backgroundColor: colors.backgroundColor,
      tooltip: {
        trigger: 'axis' as const,
        axisPointer: {
          type: 'shadow' as const,
        },
        backgroundColor: colors.tooltipBg,
        textStyle: {
          color: colors.tooltipTextColor,
        },
        borderColor: colors.tooltipBorderColor,
        formatter: (params: Array<{ name: string; value: number }>) => {
          const param = params[0]
          if (!param) return ''
          const value = param.value
          const sign = value > 0 ? '+' : ''
          return `<strong>${param.name}</strong><br/>涨跌幅: ${sign}${value.toFixed(2)}%`
        },
      },
      grid: {
        left: '3%',
        right: '8%',
        bottom: '3%',
        top: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'value' as const,
        axisLabel: {
          color: colors.secondaryTextColor,
          formatter: '{value}%',
        },
        splitLine: {
          lineStyle: {
            color: colors.gridBorderColor,
          },
        },
      },
      yAxis: {
        type: 'category' as const,
        data: reversed.map((t) => t.name),
        axisLabel: {
          color: colors.textColor,
          width: 100,
          overflow: 'truncate' as const,
        },
        axisLine: {
          lineStyle: {
            color: colors.gridBorderColor,
          },
        },
      },
      series: [
        {
          type: 'bar' as const,
          data: reversed.map((t) => {
            const pct = Number(t.rise_fall_pct)
            return {
              value: pct,
              itemStyle: {
                color: pct > 0
                  ? RISE_FALL_COLORS.rise
                  : pct < 0
                    ? RISE_FALL_COLORS.fall
                    : RISE_FALL_COLORS.neutral,
                borderRadius: [0, 4, 4, 0],
              },
            }
          }),
          barWidth: '60%',
          label: {
            show: true,
            position: 'right' as const,
            formatter: (params: { value: number }) => {
              const value = params.value
              const sign = value > 0 ? '+' : ''
              return `${sign}${value.toFixed(2)}%`
            },
            color: colors.textColor,
            fontSize: 12,
          },
        },
      ],
    }
  }, [top10, colors])

  return (
    <div className={cn('w-full', className)}>
      <ReactEChartsCore
        echarts={echarts}
        option={option}
        style={{ height: '300px', width: '100%' }}
        opts={{ renderer: 'canvas' }}
        notMerge={true}
      />
    </div>
  )
})
