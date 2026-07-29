import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'

const SETTINGS_LINKS = [
  { to: '/settings/models', label: '模型设置' },
  { to: '/settings/calendar', label: '交易日历' },
  { to: '/settings/integrations', label: '数据源' },
  { to: '/settings/shortcuts', label: '快捷键' },
  { to: '/settings/account', label: '账号设置' },
] as const

export function SettingsSubnav({ className = '' }: { className?: string }) {
  return (
    <nav
      aria-label="设置分区"
      className={cn(
        'grid h-9 w-fit max-w-full grid-flow-col auto-cols-fr items-stretch gap-0.5 rounded-xl border border-border bg-muted/40 p-0.5',
        className
      )}
      data-testid="settings-subnav"
    >
      {SETTINGS_LINKS.map((link) => (
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
  )
}
