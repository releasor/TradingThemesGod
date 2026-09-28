import { useEffect, useMemo, useState } from 'react'

import { cn } from '@/lib/utils'
import { extractVariables, fillVariables } from '@/features/prompt-workbench/domain/variables'

export function VariableFillDialog({
  body,
  open,
  onClose,
  onFilled,
}: {
  body: string
  open: boolean
  onClose: () => void
  onFilled: (text: string) => void
}) {
  const names = useMemo(() => extractVariables(body), [body])
  const [values, setValues] = useState<Record<string, string>>({})

  useEffect(() => {
    if (open) setValues({})
  }, [open, body])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="填写变量"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="w-full max-w-md rounded-xl border border-border bg-card p-5 shadow-sm">
        <h3 className="text-lg font-semibold">填写变量</h3>
        <div className="mt-4 space-y-3">
          {names.length === 0 ? (
            <p className="text-sm text-muted-foreground">没有检测到变量</p>
          ) : (
            names.map((name) => (
              <label key={name} className="block text-sm">
                <span className="mb-1 block text-muted-foreground">{name}</span>
                <input
                  className="h-9 w-full rounded-md border border-input bg-background px-3"
                  value={values[name] ?? ''}
                  onChange={(e) =>
                    setValues((prev) => ({ ...prev, [name]: e.target.value }))
                  }
                />
              </label>
            ))
          )}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            className="inline-flex h-9 items-center rounded-md border border-input px-3 text-sm hover:bg-accent"
            onClick={onClose}
          >
            取消
          </button>
          <button
            type="button"
            className={cn(
              'inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm text-primary-foreground',
              'hover:bg-primary/90'
            )}
            onClick={() => {
              onFilled(fillVariables(body, values))
              onClose()
            }}
          >
            确认
          </button>
        </div>
      </div>
    </div>
  )
}
