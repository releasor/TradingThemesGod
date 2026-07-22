const SOURCE_COLORS: Record<string, string> = {
  新浪财经: '#2563eb',
  东方财富: '#dc2626',
  华尔街见闻: '#7c3aed',
  同花顺: '#ea580c',
  财联社: '#0891b2',
  证券时报: '#059669',
  上海证券报: '#4f46e5',
  中国证券报: '#be123c',
  央视财经: '#b91c1c',
  巨潮资讯: '#0284c7',
  上交所: '#0f766e',
  深交所: '#15803d',
  北交所: '#a16207',
  证监会: '#9333ea',
  中国人民银行: '#c2410c',
  国家统计局: '#0369a1',
  国家发改委: '#9f1239',
  第一财经: '#6d28d9',
  雪球: '#16a34a',
}

const FALLBACK_COLORS = ['#2563eb', '#dc2626', '#7c3aed', '#059669', '#ea580c', '#0891b2']

export function getNewsChannelColor(source: string): string {
  const configuredColor = SOURCE_COLORS[source]
  if (configuredColor) return configuredColor

  let hash = 0
  for (const character of source) hash = (hash * 31 + character.charCodeAt(0)) >>> 0
  return FALLBACK_COLORS[hash % FALLBACK_COLORS.length]
}
