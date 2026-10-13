import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useToastContext } from '@/App'
import {
  createOsJournal,
  deleteOsJournal,
  listOsJournal,
  type JournalKind,
} from '@/features/personal-os/api/journal'
import { PinToDashboardButton } from '@/features/personal-os/components/PinToDashboardButton'
import { useOsPinnedSet } from '@/features/personal-os/hooks/useOsPinnedSet'
import { cn } from '@/lib/utils'

const panel = 'rounded-xl border border-border bg-card p-3 sm:p-4'
const field =
  'w-full rounded-md border border-input bg-background px-3 py-2 text-base sm:text-sm'
const btnPrimary =
  'inline-flex h-9 items-center justify-center rounded-md bg-primary px-3 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50'

const KINDS: { value: JournalKind; label: string }[] = [
  { value: 'diet', label: '饮食' },
  { value: 'training', label: '训练' },
  { value: 'sleep', label: '睡眠' },
  { value: 'schedule', label: '日程' },
]

export function OsJournalPage() {
  const toast = useToastContext()
  const queryClient = useQueryClient()
  const { isPinned } = useOsPinnedSet()
  const [kind, setKind] = useState<JournalKind>('diet')
  const [note, setNote] = useState('')
  const [payloadText, setPayloadText] = useState('{}')
  const [filterKind, setFilterKind] = useState<JournalKind | ''>('')

  const { data: entries = [], isFetching } = useQuery({
    queryKey: ['os-journal', filterKind],
    queryFn: () =>
      listOsJournal(filterKind ? { kind: filterKind } : undefined),
  })

  const create = useMutation({
    mutationFn: () => {
      let payload: Record<string, unknown> = {}
      try {
        payload = JSON.parse(payloadText || '{}') as Record<string, unknown>
      } catch {
        throw new Error('payload 需为合法 JSON')
      }
      return createOsJournal({
        kind,
        occurred_at: new Date().toISOString(),
        payload,
        note: note.trim() || undefined,
      })
    },
    onSuccess: async () => {
      setNote('')
      setPayloadText('{}')
      await queryClient.invalidateQueries({ queryKey: ['os-journal'] })
      toast.success('日志已记录')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div
      className="grid h-full min-h-0 gap-2 overflow-y-auto overscroll-contain sm:gap-3 lg:grid-cols-[22rem_minmax(0,1fr)] lg:overflow-hidden"
      data-testid="os-journal-page"
    >
      <section className={cn(panel, 'space-y-3')}>
        <h2 className="text-sm font-semibold">记一条</h2>
        <p className="text-xs text-muted-foreground">
          先攒 2–4 周饮食/训练/睡眠/日程，再让日报与决策「开图」。此处是仪表盘入口，不是医疗诊断。
        </p>
        <label className="block space-y-1 text-sm">
          <span className="text-muted-foreground">类型</span>
          <select
            className={field}
            value={kind}
            onChange={(e) => setKind(e.target.value as JournalKind)}
          >
            {KINDS.map((k) => (
              <option key={k.value} value={k.value}>
                {k.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-muted-foreground">备注</span>
          <textarea
            className={cn(field, 'min-h-[5rem] resize-y')}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="例如：午餐沙拉 / 深蹲 5x5 / 睡 7h"
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-muted-foreground">结构化字段（JSON）</span>
          <textarea
            className={cn(field, 'min-h-[5rem] font-mono text-xs resize-y')}
            value={payloadText}
            onChange={(e) => setPayloadText(e.target.value)}
          />
        </label>
        <button
          type="button"
          className={btnPrimary}
          disabled={create.isPending}
          onClick={() => create.mutate()}
        >
          保存日志
        </button>
      </section>

      <section className={cn(panel, 'flex min-h-0 flex-col gap-3 lg:overflow-hidden')}>
        <div className="flex shrink-0 items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">最近记录</h2>
          <select
            className={cn(field, 'h-9 max-w-[10rem]')}
            value={filterKind}
            onChange={(e) => setFilterKind(e.target.value as JournalKind | '')}
          >
            <option value="">全部</option>
            {KINDS.map((k) => (
              <option key={k.value} value={k.value}>
                {k.label}
              </option>
            ))}
          </select>
        </div>
        <ul className="min-h-0 flex-1 space-y-2 overflow-y-auto">
          {isFetching ? (
            <li className="text-sm text-muted-foreground">加载中…</li>
          ) : entries.length === 0 ? (
            <li className="space-y-1 text-sm text-muted-foreground">
              <p>暂无日志。从今天一条饮食或睡眠开始即可。</p>
              <p className="text-xs">数据攒起来后，再到日报与决策里用；系统先跑起来比完美记录更重要。</p>
            </li>
          ) : (
            entries.map((e) => (
              <li key={e.id} className="rounded-lg border border-border p-3 text-sm">
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span className="font-medium">
                    {KINDS.find((k) => k.value === e.kind)?.label ?? e.kind}
                  </span>
                  <div className="flex items-center gap-1">
                    <PinToDashboardButton
                      sourceType="journal"
                      sourceId={e.id}
                      pinned={isPinned('journal', e.id)}
                      compact
                    />
                    <button
                      type="button"
                      className="text-xs text-muted-foreground hover:text-destructive"
                      onClick={async () => {
                        await deleteOsJournal(e.id)
                        await queryClient.invalidateQueries({ queryKey: ['os-journal'] })
                      }}
                    >
                      删除
                    </button>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  {new Date(e.occurred_at).toLocaleString()}
                </p>
                {e.note ? <p className="mt-1 whitespace-pre-wrap">{e.note}</p> : null}
                {e.payload && Object.keys(e.payload).length > 0 ? (
                  <pre className="mt-1 overflow-x-auto text-xs text-muted-foreground">
                    {JSON.stringify(e.payload)}
                  </pre>
                ) : null}
              </li>
            ))
          )}
        </ul>
      </section>
    </div>
  )
}
