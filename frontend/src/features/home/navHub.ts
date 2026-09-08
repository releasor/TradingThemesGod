/** 登录后导航页的入口说明（href → 短描述） */

export const NAV_HUB_DESCRIPTIONS: Record<string, string> = {
  '/': '题材热度、涨跌排行与短线雷达总览',
  '/themes': '浏览、搜索与筛选全部题材',
  '/#short-term-radar': '一进二与短线机会候选',
  '/#strategy': '市场策略卡与情绪参考',
  '/review': '盘后复盘与事件梳理',
  '/ai-analysis': '个股买卖持仓 AI 研报',
  '/catalysts': '题材催化与驱动事件雷达',
  '/mining': '题材挖掘看板与笔记',
  '/mainline-graph': '主线概念图谱与关系编辑',
  '/settings/models': '大模型提供商与默认模型',
  '/settings/calendar': '交易日历同步与状态',
  '/settings/integrations': 'Tushare 等外部数据源',
  '/settings/shortcuts': '键盘快捷键一览',
  '/settings/account': '账号信息与安全',
}

export const DEFAULT_POST_AUTH_PATH = '/home'

/** 登录回跳：无效或鉴权页时落到导航页 */
export function resolvePostAuthPath(from: string | null | undefined): string {
  if (!from || !from.startsWith('/')) return DEFAULT_POST_AUTH_PATH
  if (from.startsWith('/login') || from.startsWith('/register')) {
    return DEFAULT_POST_AUTH_PATH
  }
  return from
}
