/** 主线叙事关系图（ECharts graph） */

import { memo, useMemo } from 'react'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import * as echarts from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { MainlineGraphEdgeItem, MainlineGraphNodeItem } from '@/types/mainline-graph'
import type { LifecycleStage } from '@/types/short-term'
import { useChartTheme } from '@/hooks/useChartTheme'
import { cn } from '@/lib/utils'

echarts.use([GraphChart, TooltipComponent, LegendComponent, CanvasRenderer])

const STAGE_COLORS: Record<string, string> = {
  germination: '#0ea5e9',
  fermentation: '#f59e0b',
  climax: '#f43f5e',
  divergence: '#8b5cf6',
  ebb: '#64748b',
}

function nodeSymbolSize(node: MainlineGraphNodeItem): number {
  const score = Math.max(node.mainline_score, node.strength_score, 0)
  return Math.min(56, Math.max(18, 14 + score / 4))
}

interface MainlineNarrativeChartProps {
  nodes: MainlineGraphNodeItem[]
  edges: MainlineGraphEdgeItem[]
  selectedThemeId: number | null
  onSelectTheme: (themeId: number) => void
  className?: string
}

export const MainlineNarrativeChart = memo(function MainlineNarrativeChart({
  nodes,
  edges,
  selectedThemeId,
  onSelectTheme,
  className,
}: MainlineNarrativeChartProps) {
  const { colors, isDark } = useChartTheme()

  const option = useMemo(() => {
    const chartNodes = nodes.map((node) => {
      const stage = node.lifecycle_stage as LifecycleStage
      const color = STAGE_COLORS[stage] ?? '#94a3b8'
      const selected = selectedThemeId === node.theme_id
      return {
        id: String(node.theme_id),
        name: node.theme_name || `题材 ${node.theme_id}`,
        value: node.mainline_score,
        symbolSize: nodeSymbolSize(node),
        category: node.role === 'mainline' ? 0 : node.role === 'branch' ? 1 : 2,
        itemStyle: {
          color,
          borderColor: selected ? colors.textColor : color,
          borderWidth: selected ? 3 : 1,
        },
        label: {
          show: true,
          color: colors.textColor,
          fontSize: 11,
        },
        themeId: node.theme_id,
      }
    })

    const chartLinks = edges.map((edge) => ({
      source: String(edge.from_theme_id),
      target: String(edge.to_theme_id),
      value: edge.weight,
      lineStyle: {
        width: Math.max(1, edge.weight * 4),
        type: edge.status === 'suggested' ? 'dashed' : 'solid',
        opacity: edge.status === 'suggested' ? 0.45 : 0.75,
        color: isDark ? '#94a3b8' : '#64748b',
      },
      label: {
        show: false,
      },
    }))

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: (params: { dataType?: string; name?: string; data?: { value?: number } }) => {
          if (params.dataType === 'edge') return ''
          return `${params.name ?? ''}<br/>主线分 ${params.data?.value ?? '—'}`
        },
      },
      legend: [
        {
          data: ['主线', '支线', '其他'],
          textStyle: { color: colors.secondaryTextColor },
          bottom: 0,
        },
      ],
      series: [
        {
          type: 'graph',
          layout: 'force',
          roam: true,
          draggable: true,
          categories: [{ name: '主线' }, { name: '支线' }, { name: '其他' }],
          force: {
            repulsion: 180,
            edgeLength: [60, 140],
            gravity: 0.08,
          },
          data: chartNodes,
          links: chartLinks,
          emphasis: {
            focus: 'adjacency',
            lineStyle: { width: 4 },
          },
        },
      ],
    }
  }, [nodes, edges, selectedThemeId, colors, isDark])

  if (nodes.length === 0) {
    return (
      <div
        data-testid="mainline-narrative-empty"
        className={cn(
          'flex min-h-[360px] items-center justify-center rounded-xl border border-dashed border-border text-sm text-muted-foreground',
          className
        )}
      >
        暂无叙事图节点，请先点击「生成叙事图谱」
      </div>
    )
  }

  return (
    <div data-testid="mainline-narrative-chart" className={cn('min-h-[420px]', className)}>
      <ReactEChartsCore
        echarts={echarts}
        option={option}
        style={{ height: 420, width: '100%' }}
        notMerge
        onEvents={{
          click: (params: { dataType?: string; data?: { themeId?: number } }) => {
            if (params.dataType !== 'node') return
            const themeId = params.data?.themeId
            if (themeId != null) onSelectTheme(themeId)
          },
        }}
      />
    </div>
  )
})
