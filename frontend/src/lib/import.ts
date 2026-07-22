/** 数据导入工具

提供 CSV 和 JSON 格式的数据导入功能。
*/

/** 导入格式 */
export type ImportFormat = 'csv' | 'json'

/** 导入结果 */
export interface ImportResult<T> {
  /** 是否成功 */
  success: boolean
  /** 导入的数据 */
  data: T[]
  /** 错误信息 */
  errors: string[]
  /** 总行数 */
  total: number
  /** 成功行数 */
  imported: number
}

/**
 * 从 CSV 字符串解析数据
 *
 * @param csv - CSV 字符串
 * @param columns - 列配置（key: 数据字段, title: 列标题）
 * @returns 解析结果
 */
export function parseCsv<T extends Record<string, unknown>>(
  csv: string,
  columns: { key: keyof T; title: string }[]
): ImportResult<T> {
  const lines = csv.split('\n').filter((line) => line.trim())
  const errors: string[] = []
  const data: T[] = []

  if (lines.length < 2) {
    return {
      success: false,
      data: [],
      errors: ['CSV 文件至少需要包含表头和一行数据'],
      total: 0,
      imported: 0,
    }
  }

  // 解析表头
  const headers = parseCsvLine(lines[0])
  const columnMap = new Map<string, keyof T>()

  for (const col of columns) {
    const index = headers.indexOf(col.title)
    if (index !== -1) {
      columnMap.set(col.title, col.key)
    }
  }

  // 解析数据行
  for (let i = 1; i < lines.length; i++) {
    try {
      const values = parseCsvLine(lines[i])
      const row = {} as T

      for (const [title, key] of columnMap) {
        const index = headers.indexOf(title)
        if (index !== -1 && values[index] !== undefined) {
          ;(row as Record<string, unknown>)[key as string] = values[index]
        }
      }

      data.push(row)
    } catch (error) {
      errors.push(`第 ${i + 1} 行解析失败: ${error instanceof Error ? error.message : '未知错误'}`)
    }
  }

  return {
    success: errors.length === 0,
    data,
    errors,
    total: lines.length - 1,
    imported: data.length,
  }
}

/**
 * 解析 CSV 行
 *
 * @param line - CSV 行
 * @returns 字段值数组
 */
function parseCsvLine(line: string): string[] {
  const values: string[] = []
  let current = ''
  let inQuotes = false

  for (let i = 0; i < line.length; i++) {
    const char = line[i]

    if (inQuotes) {
      if (char === '"') {
        if (i + 1 < line.length && line[i + 1] === '"') {
          // 转义的引号
          current += '"'
          i++
        } else {
          // 结束引号
          inQuotes = false
        }
      } else {
        current += char
      }
    } else {
      if (char === '"') {
        // 开始引号
        inQuotes = true
      } else if (char === ',') {
        // 字段分隔
        values.push(current.trim())
        current = ''
      } else {
        current += char
      }
    }
  }

  values.push(current.trim())
  return values
}

/**
 * 从 JSON 字符串解析数据
 *
 * @param json - JSON 字符串
 * @returns 解析结果
 */
export function parseJson<T>(json: string): ImportResult<T> {
  try {
    const parsed = JSON.parse(json)
    const data = Array.isArray(parsed) ? parsed : [parsed]

    return {
      success: true,
      data: data as T[],
      errors: [],
      total: data.length,
      imported: data.length,
    }
  } catch (error) {
    return {
      success: false,
      data: [],
      errors: [`JSON 解析失败: ${error instanceof Error ? error.message : '未知错误'}`],
      total: 0,
      imported: 0,
    }
  }
}

/**
 * 从文件导入数据
 *
 * @param file - 文件对象
 * @param columns - 列配置（CSV 格式需要）
 * @returns 解析结果
 */
export async function importFromFile<T extends Record<string, unknown>>(
  file: File,
  columns?: { key: keyof T; title: string }[]
): Promise<ImportResult<T>> {
  const content = await file.text()
  const ext = file.name.split('.').pop()?.toLowerCase()

  if (ext === 'csv') {
    if (!columns) {
      return {
        success: false,
        data: [],
        errors: ['CSV 导入需要提供列配置'],
        total: 0,
        imported: 0,
      }
    }
    return parseCsv<T>(content, columns)
  }

  if (ext === 'json') {
    return parseJson<T>(content)
  }

  return {
    success: false,
    data: [],
    errors: [`不支持的文件格式: ${ext}`],
    total: 0,
    imported: 0,
  }
}
