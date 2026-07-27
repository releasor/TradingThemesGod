import { CardNav, type CardNavItem } from '@/components/CardNav'
import { ThemeToggle } from '@/components/ThemeToggle'
import { AuthNav } from '@/components/AuthNav'
import { MarketStatusNav } from '@/components/MarketStatusNav'

export const APP_CARD_NAV_ITEMS: CardNavItem[] = [
  {
    label: '题材看板',
    tone: 'dashboard',
    links: [
      {
        label: '打开看板',
        href: '/',
        ariaLabel: '进入题材看板',
      },
      {
        label: '短线雷达',
        href: '/#short-term-radar',
        ariaLabel: '跳转到短线机会雷达',
      },
      {
        label: '策略与情绪',
        href: '/#strategy',
        ariaLabel: '查看策略与情绪卡',
      },
    ],
  },
  {
    label: '题材分析',
    tone: 'analysis',
    links: [
      { label: '题材库', href: '/themes', ariaLabel: '进入题材库' },
      { label: 'AI 个股分析', href: '/ai-analysis', ariaLabel: '打开 AI 个股分析' },
    ],
  },
  {
    label: '复盘研究',
    tone: 'review',
    links: [
      { label: '复盘台', href: '/review', ariaLabel: '进入复盘台' },
      { label: '催化雷达', href: '/catalysts', ariaLabel: '进入催化雷达' },
      { label: '题材挖掘', href: '/mining', ariaLabel: '进入题材挖掘' },
      { label: '主线图谱', href: '/mainline-graph', ariaLabel: '进入主线图谱' },
    ],
  },
  {
    label: '设置',
    tone: 'settings',
    links: [
      { label: '模型设置', href: '/settings/models', ariaLabel: '打开模型设置' },
      { label: '交易日历', href: '/settings/calendar', ariaLabel: '打开交易日历设置' },
      { label: '快捷键', href: '/settings/shortcuts', ariaLabel: '查看键盘快捷键' },
      { label: '账号设置', href: '/settings/account', ariaLabel: '打开账号设置' },
    ],
  },
]

/** 全站卡片导航：左上市场状态，右上账号与主题（同顶对齐） */
export function AppCardNav({ className = '' }: { className?: string }) {
  return (
    <div
      className={`relative flex items-start justify-center px-3 pt-3 sm:px-4 sm:pt-4 ${className}`.trim()}
      data-testid="app-card-nav"
    >
      <div className="absolute left-3 top-3 z-50 max-w-[min(22rem,calc(50%-3.5rem))] sm:left-4 sm:top-4">
        <MarketStatusNav />
      </div>
      <CardNav logoAlt="TradingThemesGod" items={APP_CARD_NAV_ITEMS} logoHref="/" />
      <div className="absolute right-3 top-3 z-50 flex h-9 items-center gap-2 sm:right-4 sm:top-4">
        <AuthNav />
        <ThemeToggle />
      </div>
    </div>
  )
}
