import { useEffect, useMemo } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  BookOpen,
  CalendarDays,
  LayoutDashboard,
  MessageSquare,
  Scale,
  Settings,
  Settings2,
  StickyNote,
} from 'lucide-react'

import { fetchModelProviders } from '@/api/model-provider'
import { AuthNav } from '@/components/AuthNav'
import { ThemeToggle } from '@/components/ThemeToggle'
import { cn } from '@/lib/utils'
import { fetchOsProfile } from '@/features/personal-os/api/profile'
import { useOsModelSelection } from '@/features/personal-os/stores/modelSelection'

const ALL_TABS = [
  {
    to: '/os/dashboard',
    label: '仪表盘',
    short: '首页',
    flag: null,
    icon: LayoutDashboard,
  },
  {
    to: '/os/chat',
    label: '对话',
    short: '对话',
    flag: 'chat' as const,
    icon: MessageSquare,
  },
  {
    to: '/os/memory',
    label: '记忆',
    short: '记忆',
    flag: 'memory' as const,
    icon: StickyNote,
  },
  {
    to: '/os/journal',
    label: '日志',
    short: '日志',
    flag: 'journal' as const,
    icon: CalendarDays,
  },
  {
    to: '/os/reports',
    label: '日报',
    short: '日报',
    flag: 'reports' as const,
    icon: BookOpen,
  },
  {
    to: '/os/decisions',
    label: '决策',
    short: '决策',
    flag: 'decisions' as const,
    icon: Scale,
  },
  {
    to: '/os/settings',
    label: '设置',
    short: '设置',
    flag: null,
    icon: Settings2,
  },
]

export function PersonalOsShell() {
  const location = useLocation()
  const providerId = useOsModelSelection((s) => s.providerId)
  const setProviderId = useOsModelSelection((s) => s.setProviderId)

  const { data: providers = [] } = useQuery({
    queryKey: ['model-providers'],
    queryFn: fetchModelProviders,
  })
  const { data: profile } = useQuery({
    queryKey: ['os-profile'],
    queryFn: fetchOsProfile,
  })

  const enabled = providers.filter((p) => p.enabled)
  const tabs = useMemo(() => {
    const flags = profile?.module_flags
    return ALL_TABS.filter((tab) => {
      if (tab.flag == null) return true
      if (!flags) return true
      return flags[tab.flag] !== false
    })
  }, [profile?.module_flags])

  useEffect(() => {
    if (providerId != null) return
    const preferred =
      enabled.find((p) => p.id === profile?.model_prefs.default_provider_id) ??
      enabled.find((p) => p.is_default) ??
      enabled[0]
    if (preferred) setProviderId(preferred.id)
  }, [enabled, providerId, profile?.model_prefs.default_provider_id, setProviderId])

  useEffect(() => {
    const previous = document.title
    document.title = '个人 AI OS'
    return () => {
      document.title = previous
    }
  }, [])

  // 路由变化时把当前底栏项滚入视野（窄屏横向溢出时）
  useEffect(() => {
    const el = document.querySelector<HTMLElement>(
      `[data-os-tab][href="${location.pathname}"]`
    )
    el?.scrollIntoView({ inline: 'center', block: 'nearest', behavior: 'smooth' })
  }, [location.pathname])

  return (
    <div
      className="relative z-10 flex h-dvh w-full flex-col overflow-hidden bg-background"
      style={{
        paddingTop: 'env(safe-area-inset-top)',
        paddingLeft: 'env(safe-area-inset-left)',
        paddingRight: 'env(safe-area-inset-right)',
      }}
      data-testid="personal-os-shell"
    >
      <header className="relative z-20 shrink-0 border-b border-border bg-card">
        {/* 顶栏：品牌 + 工具（手机上不塞满 tabs） */}
        <div className="flex h-12 w-full items-center gap-2 px-3 sm:h-14 sm:gap-3 sm:px-4 lg:px-6">
          <div className="flex min-w-0 flex-1 items-center gap-1.5 sm:gap-2">
            <Link
              to="/"
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground sm:h-8 sm:w-auto sm:gap-1 sm:px-2"
              aria-label="返回项目入口"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline text-sm">入口</span>
            </Link>
            <h1 className="truncate text-sm font-semibold tracking-tight text-foreground sm:text-base">
              个人 AI OS
            </h1>
          </div>

          {/* 桌面顶栏 tabs */}
          <nav
            className="relative z-20 hidden min-w-0 flex-1 items-center gap-1 overflow-x-auto md:flex"
            aria-label="个人 AI OS 模块"
          >
            {tabs.map((tab) => (
              <NavLink
                key={tab.to}
                to={tab.to}
                end={tab.to === '/os/dashboard'}
                data-os-tab
                className={({ isActive }) =>
                  cn(
                    'relative z-20 shrink-0 cursor-pointer rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                  )
                }
              >
                {tab.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex shrink-0 items-center gap-1 sm:gap-2">
            <select
              aria-label="选择模型"
              className="h-9 max-w-[7.5rem] rounded-md border border-input bg-background px-1.5 text-xs sm:max-w-[14rem] sm:px-2 sm:text-sm"
              value={providerId ?? ''}
              onChange={(e) =>
                setProviderId(e.target.value ? Number(e.target.value) : null)
              }
            >
              {enabled.length === 0 ? (
                <option value="">未配置模型</option>
              ) : (
                enabled.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.model})
                  </option>
                ))
              )}
            </select>
            <Link
              to="/settings/models?from=os"
              aria-label="模型设置"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-input hover:bg-accent sm:w-auto sm:gap-1 sm:px-2.5 sm:text-sm"
            >
              <Settings className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline">模型设置</span>
            </Link>
            <ThemeToggle />
            <AuthNav accountTo="/settings/account?from=os" />
          </div>
        </div>
      </header>

      <main className="min-h-0 flex-1 overflow-hidden p-2 pb-[calc(3.75rem+env(safe-area-inset-bottom))] sm:p-3 md:p-4 md:pb-4 lg:p-5">
        <Outlet />
      </main>

      <p className="hidden shrink-0 border-t border-border px-4 py-1.5 text-center text-[11px] text-muted-foreground md:block">
        个人数据可导出迁移 · AI 出草案由你拍板 · 日志/健康与决策内容不构成医嘱或投资建议
      </p>

      {/* 手机底栏导航 */}
      <nav
        className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80 md:hidden"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
        aria-label="个人 AI OS 底部导航"
      >
        <div className="flex items-stretch justify-between gap-0.5 overflow-x-auto px-1 pt-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <NavLink
                key={tab.to}
                to={tab.to}
                end={tab.to === '/os/dashboard'}
                data-os-tab
                className={({ isActive }) =>
                  cn(
                    'flex min-w-[3.25rem] flex-1 flex-col items-center justify-center gap-0.5 rounded-md px-1 py-1.5 text-[10px] font-medium',
                    isActive
                      ? 'text-primary'
                      : 'text-muted-foreground active:bg-accent'
                  )
                }
              >
                <Icon className="h-5 w-5" aria-hidden />
                <span className="truncate">{tab.short}</span>
              </NavLink>
            )
          })}
        </div>
      </nav>
    </div>
  )
}
