/** 开发环境性能监控面板

显示 Web Vitals 指标，仅在开发环境显示。
*/

import { useState, useEffect } from 'react'
import { Activity, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getMetricRating } from '@/lib/web-vitals'
import type { Metric } from 'web-vitals'

/** 性能指标数据 */
interface PerformanceMetric {
  name: string
  value: number
  rating: 'good' | 'needs-improvement' | 'poor'
  unit: string
}

/** 评级颜色 */
const ratingColors = {
  good: 'text-green-500',
  'needs-improvement': 'text-yellow-500',
  poor: 'text-red-500',
}

/**
 * 开发环境性能监控面板
 *
 * 仅在开发环境显示，展示 Web Vitals 指标。
 */
export function DevPerformancePanel() {
  const [metrics, setMetrics] = useState<PerformanceMetric[]>([])
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    // 仅在开发环境启用
    if (import.meta.env.PROD) return

    // 动态导入 web-vitals
    import('web-vitals').then(({ onLCP, onINP, onCLS, onFCP, onTTFB }) => {
      const handleMetric = (metric: Metric) => {
        setMetrics((prev) => {
          const existing = prev.find((m) => m.name === metric.name)
          if (existing) {
            return prev.map((m) =>
              m.name === metric.name
                ? { ...m, value: metric.value, rating: getMetricRating(metric.name, metric.value) }
                : m
            )
          }
          return [
            ...prev,
            {
              name: metric.name,
              value: metric.value,
              rating: getMetricRating(metric.name, metric.value),
              unit: metric.name === 'CLS' ? '' : 'ms',
            },
          ]
        })
      }

      onLCP(handleMetric)
      onINP(handleMetric)
      onCLS(handleMetric)
      onFCP(handleMetric)
      onTTFB(handleMetric)
    })
  }, [])

  // 生产环境不显示
  if (import.meta.env.PROD) return null

  return (
    <>
      {/* 触发按钮 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-4 right-4 z-50 rounded-full bg-primary p-3 text-primary-foreground shadow-lg hover:bg-primary/90"
        title="性能监控"
      >
        <Activity className="h-5 w-5" />
      </button>

      {/* 面板 */}
      {isOpen && (
        <div className="fixed bottom-16 right-4 z-50 w-64 rounded-lg border border-border bg-card p-4 shadow-lg">
          {/* 头部 */}
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">
              Web Vitals
            </h3>
            <button
              onClick={() => setIsOpen(false)}
              className="rounded p-1 text-muted-foreground hover:bg-accent"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* 指标列表 */}
          <div className="mt-3 space-y-2">
            {metrics.length === 0 ? (
              <p className="text-xs text-muted-foreground">加载中...</p>
            ) : (
              metrics.map((metric) => (
                <div
                  key={metric.name}
                  className="flex items-center justify-between"
                >
                  <span className="text-xs text-muted-foreground">
                    {metric.name}
                  </span>
                  <span
                    className={cn(
                      'text-xs font-medium',
                      ratingColors[metric.rating]
                    )}
                  >
                    {metric.name === 'CLS'
                      ? metric.value.toFixed(3)
                      : `${Math.round(metric.value)}${metric.unit}`}
                  </span>
                </div>
              ))
            )}
          </div>

          {/* 图例 */}
          <div className="mt-3 flex items-center gap-3 border-t border-border pt-3">
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-green-500" />
              <span className="text-xs text-muted-foreground">Good</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-yellow-500" />
              <span className="text-xs text-muted-foreground">OK</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 rounded-full bg-red-500" />
              <span className="text-xs text-muted-foreground">Poor</span>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
