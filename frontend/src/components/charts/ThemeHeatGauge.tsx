/** 题材热度仪表盘组件

使用 ECharts 仪表盘展示题材热度指数。
*/

import { memo, useMemo } from 'react'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import * as echarts from 'echarts/core'
import { GaugeChart } from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'
import { useChartTheme } from '@/hooks/useChartTheme'
import { cn } from '@/lib/utils'

// 注册必需的 ECharts 组件
echarts.use([GaugeChart, CanvasRenderer])

interface ThemeHeatGaugeProps {
  /** 热度值 (0-100) */
  value: number
  /** 题材名称 */
  name?: string
  /** 自定义类名 */
  className?: string
}

/**
 * 题材热度仪表盘组件
 *
 * @example
 * ```tsx
 * <ThemeHeatGauge value={85} name="人工智能" />
 * ```
 */
export const ThemeHeatGauge = memo(function ThemeHeatGauge({ value, name, className }: ThemeHeatGaugeProps) {
  const { colors, isDark } = useChartTheme()

  const option = useMemo(() => ({
    backgroundColor: 'transparent',
    series: [
      {
        type: 'gauge',
        startAngle: 200,
        endAngle: -20,
        min: 0,
        max: 100,
        splitNumber: 10,
        axisLine: {
          lineStyle: {
            width: 20,
            color: [
              [0.3, '#67e0e3'],
              [0.7, '#37a2da'],
              [1, '#fd666d'],
            ],
          },
        },
        pointer: {
          icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
          length: '12%',
          width: 20,
          offsetCenter: [0, '-60%'],
          itemStyle: {
            color: 'auto',
          },
        },
        axisTick: {
          length: 12,
          lineStyle: {
            color: 'auto',
            width: 2,
          },
        },
        splitLine: {
          length: 20,
          lineStyle: {
            color: 'auto',
            width: 3,
          },
        },
        axisLabel: {
          color: colors.secondaryTextColor,
          fontSize: 12,
          distance: -60,
          rotate: 'tangential',
          formatter: (value: number) => {
            if (value === 0) return '冷'
            if (value === 50) return '温'
            if (value === 100) return '热'
            return ''
          },
        },
        title: {
          offsetCenter: [0, '-20%'],
          fontSize: 14,
          color: colors.textColor,
        },
        detail: {
          fontSize: 32,
          offsetCenter: [0, '0%'],
          valueAnimation: true,
          formatter: (value: number) => `${value.toFixed(1)}`,
          color: 'inherit',
        },
        data: [
          {
            value: value,
            name: name || '热度',
          },
        ],
      },
    ],
  }), [value, name, colors])

  return (
    <div className={cn('w-full', className)}>
      <ReactEChartsCore
        echarts={echarts}
        option={option}
        style={{ height: '250px', width: '100%' }}
        opts={{ renderer: 'canvas' }}
        notMerge={true}
      />
    </div>
  )
})
