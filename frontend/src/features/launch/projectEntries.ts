/** 项目级主入口：仅提供各应用入口 */

export type ProjectEntry = {
  id: string
  name: string
  description: string
  ariaLabel: string
  badge: string
  to?: string
  comingSoon?: boolean
}

/** 已关闭应用路径，登录回跳时落到项目入口 */
const DISABLED_APP_PATH_PREFIXES = [
  '/dashboard',
  '/themes',
  '/ai-analysis',
  '/review',
  '/catalysts',
  '/mining',
  '/mainline-graph',
  '/settings/calendar',
  '/settings/integrations',
  '/os',
] as const

export function isTradingAppPath(path: string): boolean {
  return DISABLED_APP_PATH_PREFIXES.some(
    (prefix) =>
      path === prefix ||
      path.startsWith(`${prefix}/`) ||
      path.startsWith(`${prefix}?`) ||
      path.startsWith(`${prefix}#`)
  )
}

export const PROJECT_ENTRIES: ProjectEntry[] = [
  {
    id: 'prompt-workbench',
    name: 'Prompt 工作台',
    description: '设计、优化并管理 Prompt，自由聊天；模型与账号设置共用',
    to: '/prompt',
    ariaLabel: '进入 Prompt 工作台',
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
  if (isTradingAppPath(from)) return DEFAULT_POST_AUTH_PATH
  return from
}
