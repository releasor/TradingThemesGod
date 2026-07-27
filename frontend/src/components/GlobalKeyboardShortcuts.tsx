/** 全站键盘快捷键：在任意路由生效，避免离开看板后快捷键失效 */

import { useCallback, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { KeyboardShortcutsPanel } from '@/components/KeyboardShortcutsPanel'
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts'

export const DASHBOARD_REFRESH_EVENT = 'app:dashboard-refresh'

function focusThemeSearch(): boolean {
  const el = document.querySelector<HTMLInputElement>('[role="searchbox"]')
  if (!el) return false
  el.focus()
  return true
}

export function GlobalKeyboardShortcuts() {
  const navigate = useNavigate()
  const location = useLocation()
  const [helpOpen, setHelpOpen] = useState(false)

  const openHelp = useCallback(() => setHelpOpen(true), [])
  const closeHelp = useCallback(() => setHelpOpen(false), [])

  useKeyboardShortcuts([
    {
      key: 'r',
      action: () => {
        if (location.pathname === '/') {
          window.dispatchEvent(new CustomEvent(DASHBOARD_REFRESH_EVENT))
          return
        }
        navigate('/')
      },
      description: '刷新看板',
    },
    {
      key: 't',
      action: () => navigate('/themes'),
      description: '打开题材库',
    },
    {
      key: '/',
      action: () => {
        if (focusThemeSearch()) return
        navigate('/themes')
        window.setTimeout(() => focusThemeSearch(), 50)
        window.setTimeout(() => focusThemeSearch(), 200)
      },
      description: '聚焦搜索',
    },
    {
      key: '?',
      action: openHelp,
      description: '显示快捷键帮助',
    },
  ])

  return <KeyboardShortcutsPanel isOpen={helpOpen} onClose={closeHelp} />
}
