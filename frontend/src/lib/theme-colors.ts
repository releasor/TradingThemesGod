/** 题材相关颜色工具函数
 *
 * 热度指数和涨跌幅的颜色编码，供 ThemeCard 和 ThemeTableRow 共用。
 */

/** 根据热度指数返回颜色类名 */
export function getHeatColor(heatIndex: number): string {
  if (heatIndex >= 80) return 'text-red-600 bg-red-50'
  if (heatIndex >= 60) return 'text-orange-600 bg-orange-50'
  if (heatIndex >= 40) return 'text-yellow-600 bg-yellow-50'
  return 'text-green-600 bg-green-50'
}

/** 根据涨跌幅返回颜色类名 */
export function getRiseFallColor(pct: number): string {
  if (pct > 0) return 'text-red-600'
  if (pct < 0) return 'text-green-600'
  return 'text-muted-foreground'
}
