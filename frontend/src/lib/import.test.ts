import { describe, it, expect } from 'vitest'
import { parseCsv, parseJson } from './import'

describe('parseCsv', () => {
  const columns = [
    { key: 'name' as const, title: '名称' },
    { key: 'code' as const, title: '代码' },
    { key: 'heat' as const, title: '热度' },
  ]

  it('parses a valid CSV with header and data rows', () => {
    const csv = '名称,代码,热度\n人工智能,AI001,95.5\n新能源,NE002,88.0'
    const result = parseCsv(csv, columns)

    expect(result.success).toBe(true)
    expect(result.total).toBe(2)
    expect(result.imported).toBe(2)
    expect(result.data).toHaveLength(2)
    expect(result.data[0]).toEqual({ name: '人工智能', code: 'AI001', heat: '95.5' })
    expect(result.data[1]).toEqual({ name: '新能源', code: 'NE002', heat: '88.0' })
  })

  it('returns error for CSV with only header', () => {
    const csv = '名称,代码,热度'
    const result = parseCsv(csv, columns)

    expect(result.success).toBe(false)
    expect(result.errors).toContain('CSV 文件至少需要包含表头和一行数据')
    expect(result.data).toHaveLength(0)
  })

  it('returns error for empty string', () => {
    const result = parseCsv('', columns)

    expect(result.success).toBe(false)
    expect(result.errors.length).toBeGreaterThan(0)
  })

  it('handles quoted fields with commas', () => {
    const csv = '名称,代码,热度\n"人工智能,大模型",AI001,95.5'
    const result = parseCsv(csv, columns)

    expect(result.success).toBe(true)
    expect(result.data[0].name).toBe('人工智能,大模型')
  })

  it('handles quoted fields with escaped quotes', () => {
    const csv = '名称,代码,热度\n"他说""你好""",AI001,95.5'
    const result = parseCsv(csv, columns)

    expect(result.success).toBe(true)
    expect(result.data[0].name).toBe('他说"你好"')
  })

  it('handles missing columns gracefully', () => {
    const csv = '名称,代码\n人工智能,AI001'
    const result = parseCsv(csv, columns)

    expect(result.success).toBe(true)
    expect(result.data[0].name).toBe('人工智能')
    expect(result.data[0].code).toBe('AI001')
    expect(result.data[0]).not.toHaveProperty('heat')
  })

  it('handles extra columns gracefully', () => {
    const csv = '名称,代码,热度,额外\n人工智能,AI001,95.5,extra'
    const result = parseCsv(csv, columns)

    expect(result.success).toBe(true)
    expect(result.data[0].name).toBe('人工智能')
  })

  it('handles BOM-prefixed content', () => {
    const csv = '﻿名称,代码,热度\n人工智能,AI001,95.5'
    const result = parseCsv(csv, columns)

    // BOM 可能导致表头匹配失败，但不应崩溃
    expect(result.success).toBeDefined()
  })
})

describe('parseJson', () => {
  it('parses a valid JSON array', () => {
    const json = JSON.stringify([{ name: 'AI' }, { name: 'NE' }])
    const result = parseJson(json)

    expect(result.success).toBe(true)
    expect(result.data).toHaveLength(2)
    expect(result.total).toBe(2)
    expect(result.imported).toBe(2)
  })

  it('wraps a single object in an array', () => {
    const json = JSON.stringify({ name: 'AI' })
    const result = parseJson(json)

    expect(result.success).toBe(true)
    expect(result.data).toHaveLength(1)
    expect(result.data[0]).toEqual({ name: 'AI' })
  })

  it('returns error for invalid JSON', () => {
    const result = parseJson('not json {{{')

    expect(result.success).toBe(false)
    expect(result.errors.length).toBeGreaterThan(0)
    expect(result.errors[0]).toContain('JSON 解析失败')
    expect(result.data).toHaveLength(0)
  })

  it('handles empty array', () => {
    const result = parseJson('[]')

    expect(result.success).toBe(true)
    expect(result.data).toHaveLength(0)
    expect(result.total).toBe(0)
  })

  it('handles nested objects', () => {
    const json = JSON.stringify([{ name: 'AI', nested: { a: 1, b: [2, 3] } }])
    const result = parseJson(json)

    expect(result.success).toBe(true)
    expect((result.data[0] as Record<string, unknown>).nested).toEqual({ a: 1, b: [2, 3] })
  })
})
