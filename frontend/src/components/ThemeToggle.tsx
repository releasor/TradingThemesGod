/** 主题切换组件

支持亮色/暗色/系统主题三种模式。
*/

import { useState, useEffect } from 'react'
import { Moon, Sun, Monitor } from 'lucide-react'
import { cn } from '@/lib/utils'

/** 主题类型 */
type Theme = 'light' | 'dark' | 'system'

/** 获取系统主题偏好 */
function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/** 应用主题到 DOM */
function applyTheme(theme: Theme): void {
  const resolved = theme === 'system' ? getSystemTheme() : theme

  document.documentElement.classList.remove('light', 'dark')
  document.documentElement.classList.add(resolved)
}

/** 从 localStorage 读取主题 */
function getStoredTheme(): Theme {
  if (typeof window === 'undefined') return 'system'
  return (localStorage.getItem('theme') as Theme) || 'system'
}

/** 保存主题到 localStorage */
function setStoredTheme(theme: Theme): void {
  localStorage.setItem('theme', theme)
}

/** 主题切换 Hook */
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(getStoredTheme)

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme)
    setStoredTheme(newTheme)
    applyTheme(newTheme)
  }

  // 初始化主题
  useEffect(() => {
    applyTheme(theme)

    // 监听系统主题变化
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      if (theme === 'system') {
        applyTheme('system')
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme])

  return { theme, setTheme }
}

/** 主题切换按钮属性 */
interface ThemeToggleProps {
  className?: string
}

/** 主题选项列表（模块级常量，避免每次渲染重建） */
const THEMES: { value: Theme; icon: typeof Sun; label: string }[] = [
  { value: 'light', icon: Sun, label: '亮色' },
  { value: 'dark', icon: Moon, label: '暗色' },
  { value: 'system', icon: Monitor, label: '系统' },
]

/** 主题切换按钮 */
export function ThemeToggle({ className }: ThemeToggleProps) {
  const { theme, setTheme } = useTheme()

  return (
    <div className={cn('flex items-center rounded-lg border border-border p-1', className)}>
      {THEMES.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          className={cn(
            'rounded-md p-1.5 transition-colors',
            theme === value
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-accent hover:text-foreground'
          )}
          title={label}
        >
          <Icon className="h-4 w-4" />
        </button>
      ))}
    </div>
  )
}
