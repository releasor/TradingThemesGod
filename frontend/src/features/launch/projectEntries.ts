/** 项目级主入口：仅提供各应用入口，不包含 TradingThemesGod 内部模块 */

export type ProjectEntry = {
  id: string
  name: string
  description: string
  ariaLabel: string
  badge: string
  to?: string
  comingSoon?: boolean
}

export const PROJECT_ENTRIES: ProjectEntry[] = [
  {
    id: 'trading-themes-god',
    name: 'TradingThemesGod',
    description: 'A 股题材研究工作台：看板、题材库、复盘与催化分析',
    to: '/dashboard',
    ariaLabel: '进入 TradingThemesGod',
    badge: '应用',
  },
  {
    id: 'prompt-workbench',
    name: 'Prompt 工作台',
    description: '设计、优化并管理 Prompt，自由聊天；模型与题材台共用设置',
    to: '/prompt',
    ariaLabel: '进入 Prompt 工作台',
    badge: '应用',
  },
  {
    id: 'personal-ai-os',
    name: '个人 AI OS',
    description: '个人记忆、生活日志日报与多模型决策的可调参 AI 操作系统',
    to: '/os',
    ariaLabel: '进入个人 AI OS',
    badge: '应用',
  },
]

/** 登录后默认回到项目入口页 */
export const DEFAULT_POST_AUTH_PATH = '/'

export function resolvePostAuthPath(from: string | null | undefined): string {
  if (!from || !from.startsWith('/')) return DEFAULT_POST_AUTH_PATH
  if (from.startsWith('/login') || from.startsWith('/register')) {
    return DEFAULT_POST_AUTH_PATH
  }
  return from
}
