import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'

const SETTINGS_LINKS = [
  { to: '/settings/models', label: '模型设置' },
  { to: '/settings/calendar', label: '交易日历' },
  { to: '/settings/shortcuts', label: '快捷键' },
  { to: '/settings/account', label: '账号设置' },
] as const

export function SettingsSubnav({ className = '' }: { className?: string }) {
  return (
    <nav
      aria-label="设置分区"
      className={cn('flex flex-wrap gap-2', className)}
      data-testid="settings-subnav"
    >
      {SETTINGS_LINKS.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          className={({ isActive }) =>
            cn(
              'rounded-xl border px-3 py-1.5 text-sm transition-colors',
              isActive
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-card text-card-foreground hover:bg-accent'
            )
          }
        >
          {link.label}
        </NavLink>
      ))}
    </nav>
  )
}
