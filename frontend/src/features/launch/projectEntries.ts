/** 项目级主入口：仅提供各应用入口，不包含 TradingThemesGod 内部模块 */

export const PROJECT_ENTRIES = [
  {
    id: 'trading-themes-god',
    name: 'TradingThemesGod',
    description: 'A 股题材研究工作台：看板、题材库、复盘与催化分析',
    to: '/home',
    ariaLabel: '进入 TradingThemesGod',
    badge: '应用',
  },
  {
    id: 'studio-footer',
    name: 'Studio Footer',
    description: '创意工作室页脚演示：视线 scrub 视频与品牌排版',
    to: '/studio-footer',
    ariaLabel: '进入 Studio Footer',
    badge: '演示',
  },
] as const

/** 登录后默认回到项目入口页 */
export const DEFAULT_POST_AUTH_PATH = '/'

export function resolvePostAuthPath(from: string | null | undefined): string {
  if (!from || !from.startsWith('/')) return DEFAULT_POST_AUTH_PATH
  if (from.startsWith('/login') || from.startsWith('/register')) {
    return DEFAULT_POST_AUTH_PATH
  }
  return from
}
