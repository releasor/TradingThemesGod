/** 题材热度趋势折线图组件
 *
 * 展示题材热度指数随时间变化的趋势。
 */

import { useMemo } from 'react'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useChartTheme } from '@/hooks/useChartTheme'
import { EmptyChart } from './EmptyChart'
import { cn } from '@/lib/utils'

// 注册必需的 ECharts 组件
echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

/** 热度趋势数据点 */
export interface HeatTrendDataPoint {
  /** 日期 (YYYY-MM-DD) */
  date: string
  /** 热度值 */
  value: number
}

interface ThemeHeatTrendLineProps {
  /** 热度趋势数据 */
  data: HeatTrendDataPoint[]
  /** 自定义类名 */
  className?: string
}

/** 题材热度趋势折线图组件 */
export function ThemeHeatTrendLine({ data, className }: ThemeHeatTrendLineProps) {
  const { colors, isDark } = useChartTheme()

  if (data.length === 0) {
    return <EmptyChart className={cn('h-[300px]', className)} />
  }

  const option = useMemo(() => ({
    backgroundColor: colors.backgroundColor,
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: colors.tooltipBg,
      textStyle: {
        color: colors.tooltipTextColor,
      },
      borderColor: colors.tooltipBorderColor,
      formatter: (params: Array<{ name: string; value: number }>) => {
        const param = params[0]
        if (!param) return ''
        return `<strong>${param.name}</strong><br/>热度: ${param.value.toFixed(1)}`
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '8%',
      containLabel: true,
    },
    xAxis: {
      type: 'category' as const,
      data: data.map((d) => d.date),
      axisLabel: {
        color: colors.secondaryTextColor,
        rotate: data.length > 10 ? 45 : 0,
      },
      axisLine: {
        lineStyle: {
          color: colors.gridBorderColor,
        },
      },
      boundaryGap: false,
    },
    yAxis: {
      type: 'value' as const,
      name: '热度指数',
      nameTextStyle: {
        color: colors.secondaryTextColor,
      },
      axisLabel: {
        color: colors.secondaryTextColor,
      },
      splitLine: {
        lineStyle: {
          color: colors.gridBorderColor,
        },
      },
    },
    series: [
      {
        type: 'line' as const,
        data: data.map((d) => d.value),
        smooth: true,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: {
          width: 3,
          color: '#5470c6',
        },
        itemStyle: {
          color: '#5470c6',
          borderColor: isDark ? '#1f2937' : '#ffffff',
          borderWidth: 2,
        },
        areaStyle: {
          color: {
            type: 'linear' as const,
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: isDark ? 'rgba(84, 112, 198, 0.4)' : 'rgba(84, 112, 198, 0.3)' },
              { offset: 1, color: 'rgba(84, 112, 198, 0)' },
            ],
          },
        },
      },
    ],
  }), [data, colors, isDark])

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
}
