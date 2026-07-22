import { describe, it, expect, vi, beforeEach } from 'vitest'
import { t, setLocale, getLocale, initLocale } from './i18n'

// 模拟 localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value }),
    removeItem: vi.fn((key: string) => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
  }
})()

Object.defineProperty(window, 'localStorage', { value: localStorageMock })

describe('i18n', () => {
  beforeEach(() => {
    localStorageMock.clear()
    vi.clearAllMocks()
    // 重置为默认语言
    setLocale('zh-CN')
  })

  describe('getLocale / setLocale', () => {
    it('defaults to zh-CN', () => {
      expect(getLocale()).toBe('zh-CN')
    })

    it('setLocale changes the current locale', () => {
      setLocale('en-US')
      expect(getLocale()).toBe('en-US')
    })

    it('setLocale persists to localStorage', () => {
      setLocale('en-US')
      expect(localStorageMock.setItem).toHaveBeenCalledWith('locale', 'en-US')
    })
  })

  describe('initLocale', () => {
    it('loads locale from localStorage', () => {
      localStorageMock.getItem.mockReturnValue('en-US')
      initLocale()
      expect(getLocale()).toBe('en-US')
    })

    it('ignores invalid locale in localStorage', () => {
      localStorageMock.getItem.mockReturnValue('fr-FR')
      initLocale()
      expect(getLocale()).toBe('zh-CN')
    })

    it('keeps default when no stored locale', () => {
      localStorageMock.getItem.mockReturnValue(null as unknown as string)
      initLocale()
      expect(getLocale()).toBe('zh-CN')
    })
  })

  describe('t (translate)', () => {
    it('returns zh-CN translation by default', () => {
      expect(t('theme.heat')).toBe('热度')
      expect(t('common.loading')).toBe('加载中...')
    })

    it('returns en-US translation after locale change', () => {
      setLocale('en-US')
      expect(t('theme.heat')).toBe('Heat')
      expect(t('common.loading')).toBe('Loading...')
    })

    it('returns the key itself for missing translations', () => {
      expect(t('nonexistent.key')).toBe('nonexistent.key')
    })

    it('supports parameter substitution', () => {
      // 不存在的 key 会返回 key 本身，参数替换仍应生效
      expect(t('{name}你好', { name: '世界' })).toBe('世界你好')
      // 无参数时返回原始文本（无占位符的 key 不受影响）
      expect(t('theme.heat')).toBe('热度')
      // 多个参数同时替换
      expect(t('{a}{b}{c}', { a: '1', b: '2', c: '3' })).toBe('123')
    })

    it('returns consistent translations for all common keys', () => {
      const commonKeys = [
        'common.loading', 'common.error', 'common.retry', 'common.refresh',
        'common.search', 'common.filter', 'common.clear',
      ]
      for (const key of commonKeys) {
        const zh = t(key)
        expect(zh).not.toBe(key) // 不应返回 key 本身
        expect(zh.length).toBeGreaterThan(0)
      }
    })

    it('en-US has all the same keys as zh-CN', () => {
      setLocale('zh-CN')
      const zhKeys = [
        'common.loading', 'common.error', 'theme.heat', 'stock.code',
        'chain.upstream', 'scraper.run', 'empty.no_data', 'chart.heat_trend',
      ]
      const zhResults = zhKeys.map(k => t(k))

      setLocale('en-US')
      const enResults = zhKeys.map(k => t(k))

      // 所有 key 都应有翻译（不是返回 key 本身）
      for (let i = 0; i < zhKeys.length; i++) {
        expect(zhResults[i]).not.toBe(zhKeys[i])
        expect(enResults[i]).not.toBe(zhKeys[i])
        // 中英文应不同
        expect(zhResults[i]).not.toBe(enResults[i])
      }
    })
  })
})
