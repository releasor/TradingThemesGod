/** Web Vitals 性能监控

记录 LCP、FID、CLS 等核心性能指标。
*/

import { onLCP, onINP, onCLS, onFCP, onTTFB } from 'web-vitals'
import type { Metric } from 'web-vitals'

/** 性能指标回调函数类型 */
type ReportHandler = (metric: Metric) => void

/** 默认上报函数 - 控制台输出（开发环境） */
const defaultReport: ReportHandler = (metric) => {
  console.log(`[Web Vitals] ${metric.name}: ${metric.value.toFixed(2)} (${metric.rating})`)
}

/**
 * 初始化 Web Vitals 监控
 *
 * @param reportHandler - 自定义上报函数，默认输出到控制台
 */
export function initWebVitals(reportHandler: ReportHandler = defaultReport): void {
  // Largest Contentful Paint - 最大内容绘制
  onLCP(reportHandler)

  // Interaction to Next Paint - 交互到下次绘制
  onINP(reportHandler)

  // Cumulative Layout Shift - 累积布局偏移
  onCLS(reportHandler)

  // First Contentful Paint - 首次内容绘制
  onFCP(reportHandler)

  // Time to First Byte - 首字节时间
  onTTFB(reportHandler)
}

/**
 * 性能指标评级
 *
 * 根据 Web Vitals 官方标准评级
 */
export function getMetricRating(name: string, value: number): 'good' | 'needs-improvement' | 'poor' {
  const thresholds: Record<string, [number, number]> = {
    LCP: [2500, 4000],    // < 2.5s = good, < 4s = needs-improvement, >= 4s = poor
    INP: [200, 500],      // < 200ms = good, < 500ms = needs-improvement, >= 500ms = poor
    CLS: [0.1, 0.25],     // < 0.1 = good, < 0.25 = needs-improvement, >= 0.25 = poor
    FCP: [1800, 3000],    // < 1.8s = good, < 3s = needs-improvement, >= 3s = poor
    TTFB: [800, 1800],    // < 800ms = good, < 1.8s = needs-improvement, >= 1.8s = poor
  }

  const [good, needsImprovement] = thresholds[name] || [0, 0]

  if (value <= good) return 'good'
  if (value <= needsImprovement) return 'needs-improvement'
  return 'poor'
}
