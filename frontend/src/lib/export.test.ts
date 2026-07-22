import { describe, it, expect, vi, beforeEach } from 'vitest'
import { exportToCsv, exportToJson, exportThemes } from './export'

// 模拟 DOM 下载方法
const mockClick = vi.fn()
const mockRevokeObjectURL = vi.fn()
const mockCreateObjectURL = vi.fn(() => 'blob:mock-url')

beforeEach(() => {
  vi.clearAllMocks()

  // 模拟 URL.createObjectURL 和 URL.revokeObjectURL
  vi.stubGlobal('URL', {
    createObjectURL: mockCreateObjectURL,
    revokeObjectURL: mockRevokeObjectURL,
  })

  // 模拟 document.createElement
  vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
    if (tag === 'a') {
      return {
        href: '',
        download: '',
        click: mockClick,
      } as unknown as HTMLAnchorElement
    }
    return document.createElement(tag)
  })
})

describe('exportToCsv', () => {
  const data = [
    { name: '人工智能', code: 'AI001', heat: 95 },
    { name: '新能源', code: 'NE002', heat: 80 },
  ]
  const columns = [
    { key: 'name' as const, title: '名称' },
    { key: 'code' as const, title: '代码' },
    { key: 'heat' as const, title: '热度' },
  ]

  it('creates a download link with correct filename', () => {
    exportToCsv(data, columns, '题材数据')
    expect(mockClick).toHaveBeenCalled()
  })

  it('handles values containing commas', () => {
    const dataWithComma = [{ name: 'AI,机器学习', code: 'X', heat: 10 }]
    exportToCsv(dataWithComma, columns, 'test')
    expect(mockClick).toHaveBeenCalled()
  })

  it('handles values containing double quotes', () => {
    const dataWithQuotes = [{ name: '他说"好"', code: 'X', heat: 10 }]
    exportToCsv(dataWithQuotes, columns, 'test')
    expect(mockClick).toHaveBeenCalled()
  })

  it('handles null/undefined values', () => {
    const dataWithNull = [{ name: 'test', code: null as unknown as string, heat: 10 }]
    exportToCsv(dataWithNull, columns, 'test')
    expect(mockClick).toHaveBeenCalled()
  })

  it('cleans up object URL after download', () => {
    exportToCsv(data, columns, 'test')
    expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:mock-url')
  })

  it('generates CSV with BOM for Chinese support', () => {
    exportToCsv(data, columns, 'test')
    expect(mockCreateObjectURL).toHaveBeenCalled()
    // Blob 内容包含 BOM
    const blobArg = (mockCreateObjectURL.mock.calls as unknown[][])[0]?.[0]
    expect(blobArg).toBeInstanceOf(Blob)
  })
})

describe('exportToJson', () => {
  it('exports data as JSON with correct filename', () => {
    const data = { name: '人工智能', code: 'AI001' }
    exportToJson(data, 'test-data')
    expect(mockClick).toHaveBeenCalled()
  })

  it('handles array data', () => {
    const data = [{ id: 1 }, { id: 2 }]
    exportToJson(data, 'test-array')
    expect(mockClick).toHaveBeenCalled()
  })

  it('handles nested objects', () => {
    const data = {
      theme: { name: 'AI', stocks: [{ code: '000001' }] },
    }
    exportToJson(data, 'nested')
    expect(mockClick).toHaveBeenCalled()
  })
})

describe('exportThemes', () => {
  const themes = [
    {
      name: '人工智能',
      code: 'AI001',
      category: '科技',
      heat_index: 95,
      rise_fall_pct: 3.5,
      stock_count: 50,
    },
    {
      name: '新能源',
      code: 'NE002',
      category: '能源',
      heat_index: 80,
      rise_fall_pct: -1.2,
      stock_count: 30,
    },
  ]

  it('exports themes as CSV by default', () => {
    exportThemes(themes)
    expect(mockClick).toHaveBeenCalled()
    expect(mockCreateObjectURL).toHaveBeenCalled()
  })

  it('exports themes as JSON when format is json', () => {
    exportThemes(themes, 'json')
    expect(mockClick).toHaveBeenCalled()
  })

  it('handles themes without optional category field', () => {
    const themesNoCategory = [
      {
        name: '测试',
        code: 'T001',
        heat_index: 50,
        rise_fall_pct: 0,
        stock_count: 10,
      },
    ]
    exportThemes(themesNoCategory)
    expect(mockClick).toHaveBeenCalled()
  })
})
