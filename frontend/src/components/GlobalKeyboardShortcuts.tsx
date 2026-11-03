/** 全站键盘快捷键：题材/股票相关快捷键已关闭 */

import { useCallback, useState } from 'react'
import { KeyboardShortcutsPanel } from '@/components/KeyboardShortcutsPanel'
import { useKeyboardShortcuts } from '@/hooks/useKeyboardShortcuts'

export const DASHBOARD_REFRESH_EVENT = 'app:dashboard-refresh'

export function GlobalKeyboardShortcuts() {
  const [helpOpen, setHelpOpen] = useState(false)

  const openHelp = useCallback(() => setHelpOpen(true), [])
  const closeHelp = useCallback(() => setHelpOpen(false), [])

  useKeyboardShortcuts([
    {
      key: '?',
      action: openHelp,
      description: '显示快捷键帮助',
    },
  ])

  return <KeyboardShortcutsPanel isOpen={helpOpen} onClose={closeHelp} />
}
