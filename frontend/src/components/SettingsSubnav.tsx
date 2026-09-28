import { useEffect } from 'react'
import { Link, NavLink, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { LogOut } from 'lucide-react'
import { ThemeToggle } from '@/components/ThemeToggle'
import { useAuthStore } from '@/stores/auth'
import { cn } from '@/lib/utils'

const THEME_SETTINGS_LINKS = [
  { to: '/settings/models', label: '模型设置' },
  { to: '/settings/calendar', label: '交易日历' },
  { to: '/settings/integrations', label: '数据源' },
  { to: '/settings/shortcuts', label: '快捷键' },
  { to: '/settings/account', label: '账号设置' },
] as const

const PROMPT_SETTINGS_LINKS = [
  { to: '/settings/models?from=prompt', label: '模型设置' },
  { to: '/settings/account?from=prompt', label: '账号设置' },
] as const

export function SettingsSubnav({ className = '' }: { className?: string }) {
  const [searchParams] = useSearchParams()
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const fromPrompt = searchParams.get('from') === 'prompt'
  const links = fromPrompt ? PROMPT_SETTINGS_LINKS : THEME_SETTINGS_LINKS
  const backTo = fromPrompt ? '/prompt' : '/'
  const token = useAuthStore((state) => state.token)
  const user = useAuthStore((state) => state.user)
  const clearAuth = useAuthStore((state) => state.clearAuth)
  const showLogout = pathname === '/settings/account' && Boolean(token)

  useEffect(() => {
    if (!fromPrompt) return
    const previous = document.title
    document.title = 'Prompt 工作台'
    return () => {
      document.title = previous
    }
  }, [fromPrompt])

  return (
    <div
      className={cn(
        'flex flex-wrap items-center justify-between gap-3',
        className
      )}
    >
      <nav
        aria-label="设置分区"
        className="grid h-9 w-fit max-w-full grid-flow-col auto-cols-fr items-stretch gap-0.5 rounded-xl border border-border bg-muted/40 p-0.5"
        data-testid="settings-subnav"
      >
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end
            className={({ isActive }) =>
              cn(
                // 固定行高；激活态只用底色，不加 ring/shadow，避免看起来比旁边高
                'inline-flex h-full items-center justify-center whitespace-nowrap rounded-lg px-3 text-sm font-medium leading-none transition-colors',
                isActive
                  ? 'bg-background text-foreground'
                  : 'font-normal text-muted-foreground hover:bg-background/50 hover:text-foreground'
              )
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>
      <div className="ml-auto flex items-center gap-2">
        <ThemeToggle />
        {showLogout ? (
          <>
            {user?.username ? (
              <span
                className="hidden max-w-[10rem] truncate text-sm text-muted-foreground sm:inline"
                title={user.username}
                data-testid="settings-current-user"
              >
                {user.username}
              </span>
            ) : null}
            <button
              type="button"
              onClick={() => {
                clearAuth()
                navigate('/login')
              }}
              className="inline-flex h-9 items-center gap-1.5 rounded-xl border border-border px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              aria-label="退出登录"
            >
              <LogOut className="h-3.5 w-3.5" />
              退出
            </button>
          </>
        ) : null}
        <Link
          to={backTo}
          className="inline-flex h-9 items-center rounded-xl border border-border px-3 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          返回
        </Link>
      </div>
    </div>
  )
}
