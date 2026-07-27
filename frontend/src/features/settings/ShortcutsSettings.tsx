import { Keyboard } from 'lucide-react'
import { AppCardNav } from '@/components/AppCardNav'
import { SettingsSubnav } from '@/components/SettingsSubnav'
import { GlowCard } from '@/components/GlowCard'
import { KEYBOARD_SHORTCUTS } from '@/components/keyboardShortcuts'

/** 快捷键设置页 */
export function ShortcutsSettings() {
  return (
    <div className="min-h-screen">
      <AppCardNav />
      <main className="mx-auto w-full max-w-none space-y-5 px-3 py-6 sm:px-4 lg:px-5 xl:px-6">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Keyboard className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">快捷键</h1>
              <p className="text-sm text-muted-foreground">全站可用的键盘操作一览</p>
            </div>
          </div>
          <SettingsSubnav />
        </div>

        <GlowCard>
          <div className="space-y-3 p-5">
            {KEYBOARD_SHORTCUTS.map((shortcut) => (
              <div
                key={shortcut.key}
                className="flex items-center justify-between gap-4 border-b border-border/60 py-2 last:border-0"
              >
                <span className="text-sm text-muted-foreground">{shortcut.description}</span>
                <kbd className="inline-flex h-7 min-w-[28px] items-center justify-center rounded-lg border border-border bg-muted px-2 text-xs font-medium">
                  {shortcut.key}
                </kbd>
              </div>
            ))}
          </div>
        </GlowCard>
      </main>
    </div>
  )
}
