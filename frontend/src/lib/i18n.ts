/** 国际化基础支持

提供简单的国际化功能，支持多语言扩展。
*/

/** 语言类型 */
export type Locale = 'zh-CN' | 'en-US'

/** 翻译字典 */
type TranslationDict = Record<string, string>

/** 翻译资源 */
const translations: Record<Locale, TranslationDict> = {
  'zh-CN': {
    // 通用
    'common.loading': '加载中...',
    'common.error': '加载失败',
    'common.retry': '重试',
    'common.refresh': '刷新',
    'common.search': '搜索',
    'common.filter': '筛选',
    'common.clear': '清除',
    'common.save': '保存',
    'common.cancel': '取消',
    'common.confirm': '确认',
    'common.back': '返回',
    'common.more': '更多',

    // 题材
    'theme.dashboard': '题材看板',
    'theme.library': '题材库',
    'theme.detail': '题材详情',
    'theme.name': '题材名称',
    'theme.heat': '热度',
    'theme.rise_fall': '涨跌幅',
    'theme.stock_count': '关联股票',
    'theme.category': '分类',
    'theme.tags': '标签',

    // 股票
    'stock.code': '股票代码',
    'stock.name': '股票名称',
    'stock.industry': '所属行业',
    'stock.market_cap': '总市值',
    'stock.price': '当前价格',
    'stock.events': '相关事件',

    // 产业链
    'chain.upstream': '上游',
    'chain.midstream': '中游',
    'chain.downstream': '下游',
    'chain.representative': '代表企业',

    // 爬虫
    'scraper.run': '运行爬虫',
    'scraper.status': '爬虫状态',
    'scraper.completed': '已完成',
    'scraper.running': '运行中',
    'scraper.failed': '失败',

    // 空状态
    'empty.no_data': '暂无数据',
    'empty.no_results': '未找到结果',
    'empty.error': '加载失败',

    // 图表
    'chart.heat_trend': '热度趋势',
    'chart.rise_fall': '涨跌幅 Top 10',
    'chart.chain_distribution': '产业链分布',
    'chart.no_data': '暂无数据',
  },
  'en-US': {
    // Common
    'common.loading': 'Loading...',
    'common.error': 'Load failed',
    'common.retry': 'Retry',
    'common.refresh': 'Refresh',
    'common.search': 'Search',
    'common.filter': 'Filter',
    'common.clear': 'Clear',
    'common.save': 'Save',
    'common.cancel': 'Cancel',
    'common.confirm': 'Confirm',
    'common.back': 'Back',
    'common.more': 'More',

    // Theme
    'theme.dashboard': 'Theme Dashboard',
    'theme.library': 'Theme Library',
    'theme.detail': 'Theme Detail',
    'theme.name': 'Theme Name',
    'theme.heat': 'Heat',
    'theme.rise_fall': 'Rise/Fall',
    'theme.stock_count': 'Stocks',
    'theme.category': 'Category',
    'theme.tags': 'Tags',

    // Stock
    'stock.code': 'Stock Code',
    'stock.name': 'Stock Name',
    'stock.industry': 'Industry',
    'stock.market_cap': 'Market Cap',
    'stock.price': 'Price',
    'stock.events': 'Events',

    // Chain
    'chain.upstream': 'Upstream',
    'chain.midstream': 'Midstream',
    'chain.downstream': 'Downstream',
    'chain.representative': 'Representative',

    // Scraper
    'scraper.run': 'Run Scraper',
    'scraper.status': 'Status',
    'scraper.completed': 'Completed',
    'scraper.running': 'Running',
    'scraper.failed': 'Failed',

    // Empty
    'empty.no_data': 'No data',
    'empty.no_results': 'No results found',
    'empty.error': 'Load failed',

    // Chart
    'chart.heat_trend': 'Heat Trend',
    'chart.rise_fall': 'Top 10 Rise/Fall',
    'chart.chain_distribution': 'Chain Distribution',
    'chart.no_data': 'No data',
  },
}

/** 当前语言 */
let currentLocale: Locale = 'zh-CN'

/**
 * 设置当前语言
 *
 * @param locale - 语言代码
 */
export function setLocale(locale: Locale): void {
  currentLocale = locale
  localStorage.setItem('locale', locale)
}

/**
 * 获取当前语言
 */
export function getLocale(): Locale {
  return currentLocale
}

/**
 * 初始化语言设置
 */
export function initLocale(): void {
  const stored = localStorage.getItem('locale') as Locale
  if (stored && translations[stored]) {
    currentLocale = stored
  }
}

/**
 * 翻译函数
 *
 * @param key - 翻译键
 * @param params - 替换参数
 * @returns 翻译后的文本
 *
 * @example
 * ```ts
 * t('theme.heat') // '热度'
 * t('theme.stock_count') // '关联股票'
 * ```
 */
export function t(key: string, params?: Record<string, string | number>): string {
  let text = translations[currentLocale]?.[key] || key

  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
    })
  }

  return text
}
