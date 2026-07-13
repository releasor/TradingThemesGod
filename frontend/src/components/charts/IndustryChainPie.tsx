/** 产业链股票分布饼图组件
 *
 * 展示题材关联股票在上游/中游/下游的分布情况。
 */

import { memo, useMemo } from 'react'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import * as echarts from 'echarts/core'
import { PieChart } from 'echarts/charts'
import {
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { IndustryChainBrief } from '@/types/theme'
import { useChartTheme } from '@/hooks/useChartTheme'
import { CHAIN_LEVEL_COLORS } from '@/lib/chart-colors'
import { EmptyChart } from './EmptyChart'
import { cn } from '@/lib/utils'

// 注册必需的 ECharts 组件
echarts.use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])

interface IndustryChainPieProps {
  /** 产业链数据（按层级分组） */
  chains: {
    upstream: IndustryChainBrief[]
    midstream: IndustryChainBrief[]
    downstream: IndustryChainBrief[]
  }
  /** 自定义类名 */
  className?: string
}

/** 产业链层级名称映射 */
const LEVEL_NAMES: Record<string, string> = {
  upstream: '上游',
  midstream: '中游',
  downstream: '下游',
}

/** 产业链股票分布饼图组件 */
export const IndustryChainPie = memo(function IndustryChainPie({ chains, className }: IndustryChainPieProps) {
  const { colors, isDark } = useChartTheme()

  // 计算各层级的环节数量
  const data = useMemo(
    () =>
      [
        { name: LEVEL_NAMES.upstream, value: chains.upstream.length, level: 'upstream' },
        { name: LEVEL_NAMES.midstream, value: chains.midstream.length, level: 'midstream' },
        { name: LEVEL_NAMES.downstream, value: chains.downstream.length, level: 'downstream' },
      ].filter((d) => d.value > 0),
    [chains],
  )

  const option = useMemo(() => {
    if (data.length === 0) return null
    return {
      backgroundColor: colors.backgroundColor,
      tooltip: {
        trigger: 'item' as const,
        backgroundColor: colors.tooltipBg,
        textStyle: {
          color: colors.tooltipTextColor,
        },
        borderColor: colors.tooltipBorderColor,
        formatter: (params: { name: string; value: number; percent: number }) => {
          return `<strong>${params.name}</strong><br/>环节数: ${params.value}<br/>占比: ${params.percent.toFixed(1)}%`
        },
      },
      legend: {
        bottom: '5%',
        left: 'center' as const,
        textStyle: {
          color: colors.textColor,
        },
        itemGap: 20,
      },
      series: [
        {
          type: 'pie' as const,
          radius: ['40%', '70%'],
          center: ['50%', '45%'],
          avoidLabelOverlap: true,
          itemStyle: {
            borderRadius: 6,
            borderColor: isDark ? '#1f2937' : '#ffffff',
            borderWidth: 2,
          },
          label: {
            show: true,
            formatter: (params: { name: string; value: number; percent: number }) => {
              return `${params.name}\n${params.value} (${params.percent.toFixed(0)}%)`
            },
            color: colors.textColor,
            fontSize: 12,
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 14,
              fontWeight: 'bold' as const,
            },
          },
          data: data.map((d) => ({
            ...d,
            itemStyle: {
              color: CHAIN_LEVEL_COLORS[d.level as keyof typeof CHAIN_LEVEL_COLORS],
            },
          })),
        },
      ],
    }
  }, [data, colors, isDark])

  if (!option) {
    return <EmptyChart className={cn('h-[300px]', className)} />
  }

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
