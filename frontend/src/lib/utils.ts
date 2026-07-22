import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** 格式化涨跌幅显示（中国股市惯例：红涨绿跌前缀 +/-） */
export function formatRiseFall(pct: number | null | undefined): string {
  if (pct === null || pct === undefined) return '-'
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

/** 格式化市值显示（亿元/万元） */
export function formatMarketCap(value: number | null | undefined): string {
  if (value === null || value === undefined) return '-'
  if (value >= 1_0000_0000) return `${(value / 1_0000_0000).toFixed(2)}亿`
  if (value >= 1_0000) return `${(value / 1_0000).toFixed(2)}万`
  return value.toFixed(2)
}
