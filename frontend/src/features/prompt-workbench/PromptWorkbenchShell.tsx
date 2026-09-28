import { useEffect } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Settings } from 'lucide-react'

import { fetchModelProviders } from '@/api/model-provider'
import { AuthNav } from '@/components/AuthNav'
import { ThemeToggle } from '@/components/ThemeToggle'
import { cn } from '@/lib/utils'
import { usePromptModelSelection } from '@/features/prompt-workbench/stores/modelSelection'

const TABS = [
  { to: '/prompt/optimize', label: '优化' },
  { to: '/prompt/design', label: '设计' },
  { to: '/prompt/library', label: '我的 Prompt' },
  { to: '/prompt/chat', label: '自由聊天' },
] as const

export function PromptWorkbenchShell() {
  const providerId = usePromptModelSelection((s) => s.providerId)
  const setProviderId = usePromptModelSelection((s) => s.setProviderId)

  const { data: providers = [] } = useQuery({
    queryKey: ['model-providers'],
    queryFn: fetchModelProviders,
  })

  const enabled = providers.filter((p) => p.enabled)

  useEffect(() => {
    if (providerId != null) return
    const preferred = enabled.find((p) => p.is_default) ?? enabled[0]
    if (preferred) setProviderId(preferred.id)
  }, [enabled, providerId, setProviderId])

  useEffect(() => {
    const previous = document.title
    document.title = 'Prompt 工作台'
    return () => {
      document.title = previous
    }
  }, [])

  return (
    <div
      className="flex h-dvh w-full flex-col overflow-hidden bg-background"
      data-testid="prompt-workbench-shell"
    >
      <header className="shrink-0 border-b border-border bg-card">
        <div className="flex h-14 w-full items-center gap-3 px-4 lg:gap-4 lg:px-6">
          <div className="min-w-0 shrink-0">
            <h1 className="truncate text-base font-semibold tracking-tight text-foreground">
              Prompt 工作台
            </h1>
          </div>

          <nav
            className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto"
            aria-label="Prompt 工作台模块"
          >
            {TABS.map((tab) => (
              <NavLink
                key={tab.to}
                to={tab.to}
                className={({ isActive }) =>
                  cn(
                    'shrink-0 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
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

          <div className="flex shrink-0 items-center gap-2">
            <select
              aria-label="选择模型"
              className="h-9 max-w-[10rem] rounded-md border border-input bg-background px-2 text-sm sm:max-w-[14rem]"
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
              to="/settings/models?from=prompt"
              aria-label="模型设置"
              className="inline-flex h-9 items-center gap-1 rounded-md border border-input px-2.5 text-sm hover:bg-accent"
            >
              <Settings className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline">模型设置</span>
            </Link>
            <ThemeToggle />
            <AuthNav accountTo="/settings/account?from=prompt" />
          </div>
        </div>
      </header>

      <main className="min-h-0 flex-1 overflow-hidden p-3 sm:p-4 lg:p-5">
        <Outlet />
      </main>
    </div>
  )
}
