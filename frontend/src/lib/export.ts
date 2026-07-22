/** 数据导出工具

提供 CSV 和 JSON 格式的数据导出功能。
*/

/** 导出格式 */
export type ExportFormat = 'csv' | 'json'

/** 导出选项 */
export interface ExportOptions {
  /** 文件名（不含扩展名） */
  filename: string
  /** 导出格式 */
  format: ExportFormat
}

/**
 * 将数据导出为 CSV 格式
 *
 * @param data - 要导出的数据数组
 * @param columns - 列配置（key: 数据字段, title: 列标题）
 */
export function exportToCsv<T extends Record<string, unknown>>(
  data: T[],
  columns: { key: keyof T; title: string }[],
  filename: string
): void {
  // 生成 CSV 头
  const header = columns.map((col) => `"${col.title}"`).join(',')

  // 生成 CSV 行
  const rows = data.map((row) =>
    columns
      .map((col) => {
        const value = row[col.key]
        // 处理包含逗号或引号的值
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`
        }
        return value ?? ''
      })
      .join(',')
  )

  // 组合 CSV 内容
  const csv = [header, ...rows].join('\n')

  // 添加 BOM 以支持中文
  const bom = '﻿'
  downloadFile(bom + csv, `${filename}.csv`, 'text/csv;charset=utf-8')
}

/**
 * 将数据导出为 JSON 格式
 *
 * @param data - 要导出的数据
 * @param filename - 文件名
 */
export function exportToJson<T>(data: T, filename: string): void {
  const json = JSON.stringify(data, null, 2)
  downloadFile(json, `${filename}.json`, 'application/json')
}

/**
 * 下载文件
 *
 * @param content - 文件内容
 * @param filename - 文件名
 * @param mimeType - MIME 类型
 */
function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()

  // 清理
  URL.revokeObjectURL(url)
}

/**
 * 导出题材数据
 *
 * @param themes - 题材数据数组
 * @param format - 导出格式
 */
export function exportThemes(
  themes: Array<{
    name: string
    code: string
    category?: string
    heat_index: number
    rise_fall_pct: number
    stock_count: number
  }>,
  format: ExportFormat = 'csv'
): void {
  const columns = [
    { key: 'name' as const, title: '题材名称' },
    { key: 'code' as const, title: '题材代码' },
    { key: 'category' as const, title: '分类' },
    { key: 'heat_index' as const, title: '热度指数' },
    { key: 'rise_fall_pct' as const, title: '涨跌幅(%)' },
    { key: 'stock_count' as const, title: '关联股票数' },
  ]

  const timestamp = new Date().toISOString().slice(0, 10)
  const filename = `题材数据_${timestamp}`

  if (format === 'csv') {
    exportToCsv(themes, columns, filename)
  } else {
    exportToJson(themes, filename)
  }
}
