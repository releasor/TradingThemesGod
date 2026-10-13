import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useToastContext } from '@/App'
import {
  createOsNote,
  deleteOsNote,
  listOsNotes,
  updateOsNote,
} from '@/features/personal-os/api/notes'
import { fetchOsProfile, updateOsProfile } from '@/features/personal-os/api/profile'
import { PinToDashboardButton } from '@/features/personal-os/components/PinToDashboardButton'
import { useOsPinnedSet } from '@/features/personal-os/hooks/useOsPinnedSet'
import { cn } from '@/lib/utils'

const panel = 'rounded-xl border border-border bg-card p-3 sm:p-4'
const field =
  'w-full rounded-md border border-input bg-background px-3 py-2 text-base sm:text-sm'
const btn =
  'inline-flex h-9 items-center justify-center rounded-md px-3 text-sm transition-colors'
const btnPrimary = cn(btn, 'bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50')
const btnGhost = cn(btn, 'border border-input hover:bg-accent')

export function OsMemoryPage() {
  const toast = useToastContext()
  const queryClient = useQueryClient()
  const { isPinned } = useOsPinnedSet()
  const [q, setQ] = useState('')
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [displayName, setDisplayName] = useState('')
  const [goals, setGoals] = useState('')
  const [baselineText, setBaselineText] = useState('{}')
  const [hydrated, setHydrated] = useState(false)

  const { data: profile } = useQuery({
    queryKey: ['os-profile'],
    queryFn: fetchOsProfile,
  })

  const { data: notes = [], isFetching } = useQuery({
    queryKey: ['os-notes', q],
    queryFn: () => listOsNotes(q || undefined),
  })

  useEffect(() => {
    if (!profile || hydrated) return
    setDisplayName(profile.display_name ?? '')
    setGoals(profile.goals ?? '')
    setBaselineText(JSON.stringify(profile.health_baseline ?? {}, null, 2))
    setHydrated(true)
  }, [profile, hydrated])

  const saveProfile = useMutation({
    mutationFn: () => {
      let health_baseline: Record<string, unknown> = {}
      try {
        health_baseline = JSON.parse(baselineText || '{}') as Record<string, unknown>
      } catch {
        throw new Error('健康基线需为合法 JSON')
      }
      return updateOsProfile({
        display_name: displayName.trim() || null,
        goals: goals.trim() || null,
        health_baseline,
      })
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['os-profile'] })
      toast.success('档案已保存')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const saveNote = useMutation({
    mutationFn: async () => {
      if (editingId != null) {
        return updateOsNote(editingId, { title: title.trim(), body: body.trim() })
      }
      return createOsNote({ title: title.trim(), body: body.trim() })
    },
    onSuccess: async () => {
      const wasEdit = editingId != null
      setTitle('')
      setBody('')
      setEditingId(null)
      await queryClient.invalidateQueries({ queryKey: ['os-notes'] })
      toast.success(wasEdit ? '笔记已更新' : '笔记已创建')
    },
    onError: (e: Error) => toast.error(e.message || '保存失败'),
  })

  return (
    <div
      className="grid h-full min-h-0 gap-2 overflow-y-auto overscroll-contain sm:gap-3 lg:grid-cols-2 lg:overflow-hidden"
      data-testid="os-memory-page"
    >
      <section className={cn(panel, 'space-y-3 lg:overflow-y-auto')}>
        <h2 className="text-sm font-semibold">固定档案</h2>
        <label className="block space-y-1 text-sm">
          <span className="text-muted-foreground">称呼</span>
          <input
            className={field}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="怎么称呼你"
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-muted-foreground">目标</span>
          <textarea
            className={cn(field, 'min-h-[6rem] resize-y')}
            value={goals}
            onChange={(e) => setGoals(e.target.value)}
            placeholder="近期目标、原则…"
          />
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-muted-foreground">健康基线（JSON）</span>
          <textarea
            className={cn(field, 'min-h-[6rem] font-mono text-xs resize-y')}
            value={baselineText}
            onChange={(e) => setBaselineText(e.target.value)}
          />
        </label>
        <button
          type="button"
          className={btnPrimary}
          disabled={saveProfile.isPending}
          onClick={() => saveProfile.mutate()}
        >
          保存档案
        </button>
      </section>

      <section className={cn(panel, 'flex min-h-0 flex-col gap-3 lg:overflow-hidden')}>
        <div className="flex shrink-0 items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">笔记库</h2>
          <input
            className={cn(field, 'h-9 max-w-[14rem]')}
            placeholder="搜索笔记"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="space-y-2 shrink-0">
          <input
            className={field}
            placeholder="标题"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <textarea
            className={cn(field, 'min-h-[5rem] resize-y')}
            placeholder="正文（Markdown）"
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <div className="flex gap-2">
            <button
              type="button"
              className={btnPrimary}
              disabled={!title.trim() || !body.trim() || saveNote.isPending}
              onClick={() => saveNote.mutate()}
            >
              {editingId != null ? '更新笔记' : '新建笔记'}
            </button>
            {editingId != null ? (
              <button
                type="button"
                className={btnGhost}
                onClick={() => {
                  setEditingId(null)
                  setTitle('')
                  setBody('')
                }}
              >
                取消编辑
              </button>
            ) : null}
          </div>
        </div>
        <ul className="min-h-0 flex-1 space-y-2 overflow-y-auto">
          {isFetching ? (
            <li className="text-sm text-muted-foreground">加载中…</li>
          ) : notes.length === 0 ? (
            <li className="text-sm text-muted-foreground">暂无笔记</li>
          ) : (
            notes.map((n) => (
              <li key={n.id} className="rounded-lg border border-border p-3">
                <div className="mb-1 flex items-start justify-between gap-2">
                  <h3 className="text-sm font-medium">{n.title}</h3>
                  <div className="flex flex-wrap items-center justify-end gap-1">
                    <PinToDashboardButton
                      sourceType="note"
                      sourceId={n.id}
                      pinned={isPinned('note', n.id)}
                      compact
                    />
                    <button
                      type="button"
                      className="text-xs text-muted-foreground hover:text-foreground"
                      onClick={() => {
                        setEditingId(n.id)
                        setTitle(n.title)
                        setBody(n.body)
                      }}
                    >
                      编辑
                    </button>
                    <button
                      type="button"
                      className="text-xs text-muted-foreground hover:text-destructive"
                      onClick={async () => {
                        await deleteOsNote(n.id)
                        await queryClient.invalidateQueries({ queryKey: ['os-notes'] })
                      }}
                    >
                      删除
                    </button>
                  </div>
                </div>
                <p className="line-clamp-3 whitespace-pre-wrap text-xs text-muted-foreground">
                  {n.body}
                </p>
              </li>
            ))
          )}
        </ul>
      </section>
    </div>
  )
}
