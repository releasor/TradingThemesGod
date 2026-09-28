import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Copy, Pencil, Pin, Trash2, Wand2 } from 'lucide-react'

import { useToastContext } from '@/App'
import {
  createPromptItem,
  deletePromptItem,
  listPromptItems,
  updatePromptItem,
  type PromptItem,
} from '@/features/prompt-workbench/api/library'
import { VariableFillDialog } from '@/features/prompt-workbench/components/VariableFillDialog'
import { extractVariables } from '@/features/prompt-workbench/domain/variables'
import { cn } from '@/lib/utils'

const panel = 'flex min-h-0 flex-col rounded-xl border border-border bg-card'
const field = 'w-full rounded-md border border-input bg-background px-3 text-sm'
const btn =
  'inline-flex h-9 shrink-0 items-center justify-center rounded-md px-3 text-sm transition-colors'
const btnPrimary = cn(btn, 'bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50')
const btnGhost = cn(btn, 'border border-input hover:bg-accent')
const btnIcon =
  'inline-flex h-8 items-center gap-1 rounded-md border border-input px-2.5 text-xs hover:bg-accent'

export function LibraryPage() {
  const toast = useToastContext()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [q, setQ] = useState('')
  const [editing, setEditing] = useState<PromptItem | null>(null)
  const [form, setForm] = useState({
    title: '',
    body: '',
    category: '',
    tags: '',
  })
  const [fillBody, setFillBody] = useState<string | null>(null)

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['prompt-items', q],
    queryFn: () => listPromptItems(q ? { q } : undefined),
  })

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        title: form.title.trim(),
        body: form.body,
        category: form.category.trim() || null,
        tags: form.tags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
      }
      if (editing) return updatePromptItem(editing.id, payload)
      return createPromptItem(payload)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['prompt-items'] })
      setEditing(null)
      setForm({ title: '', body: '', category: '', tags: '' })
      toast.success(editing ? '已更新' : '已创建')
    },
    onError: (err: Error) => toast.error(err.message || '保存失败'),
  })

  async function copyText(text: string) {
    await navigator.clipboard.writeText(text)
    toast.success('已复制')
  }

  return (
    <div
      className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-3 overflow-y-auto lg:overflow-hidden"
      data-testid="prompt-library-page"
    >
      <div className="flex shrink-0 flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold tracking-tight">我的 Prompt</h2>
          <p className="text-sm text-muted-foreground">
            保存、搜索并用 {'{{变量}}'} 复用
          </p>
        </div>
        <input
          className={cn(field, 'h-9 sm:max-w-xs')}
          placeholder="搜索标题或内容"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="搜索 Prompt"
        />
      </div>

      <div className="grid min-h-0 gap-3 lg:grid-cols-[minmax(18rem,0.9fr)_minmax(0,1.2fr)] lg:overflow-hidden">
        <section className={cn(panel, 'min-h-[18rem] gap-3 p-4 lg:min-h-0')}>
          <h3 className="shrink-0 font-medium">
            {editing ? '编辑 Prompt' : '新建 Prompt'}
          </h3>
          <input
            className={cn(field, 'h-9 shrink-0')}
            placeholder="标题"
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
          />
          <textarea
            className={cn(field, 'min-h-0 flex-1 resize-none py-2')}
            placeholder="正文，可用 {{audience}} 这类变量"
            value={form.body}
            onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
          />
          <div className="grid shrink-0 gap-2 sm:grid-cols-2">
            <input
              className={cn(field, 'h-9')}
              placeholder="分类"
              value={form.category}
              onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
            />
            <input
              className={cn(field, 'h-9')}
              placeholder="标签（逗号分隔）"
              value={form.tags}
              onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))}
            />
          </div>
          <div className="flex shrink-0 gap-2">
            <button
              type="button"
              className={btnPrimary}
              disabled={!form.title.trim() || !form.body.trim() || saveMutation.isPending}
              onClick={() => saveMutation.mutate()}
            >
              {editing ? '保存修改' : '创建'}
            </button>
            {editing ? (
              <button
                type="button"
                className={btnGhost}
                onClick={() => {
                  setEditing(null)
                  setForm({ title: '', body: '', category: '', tags: '' })
                }}
              >
                取消
              </button>
            ) : null}
          </div>
        </section>

        <section className={cn(panel, 'min-h-[16rem] overflow-hidden lg:min-h-0')}>
          <ul className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
            {isLoading ? (
              <li className="px-1 text-sm text-muted-foreground">加载中…</li>
            ) : items.length === 0 ? (
              <li className="px-1 text-sm text-muted-foreground">暂无 Prompt</li>
            ) : (
              items.map((item) => (
                <li key={item.id}>
                  <article
                    className={cn(
                      'rounded-lg border border-border/70 bg-background/60 p-3',
                      !item.enabled && 'opacity-60'
                    )}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="font-semibold">{item.title}</h4>
                      {item.pinned ? (
                        <Pin className="h-3.5 w-3.5 text-primary" aria-label="已置顶" />
                      ) : null}
                      {item.category ? (
                        <span className="rounded-md border border-border px-2 py-0.5 text-xs text-muted-foreground">
                          {item.category}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-2 line-clamp-3 whitespace-pre-wrap text-sm text-muted-foreground">
                      {item.body}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        className={btnIcon}
                        onClick={() => {
                          if (extractVariables(item.body).length) setFillBody(item.body)
                          else void copyText(item.body)
                        }}
                      >
                        <Copy className="h-3.5 w-3.5" /> 复制
                      </button>
                      <button
                        type="button"
                        className={btnIcon}
                        onClick={() =>
                          navigate('/prompt/optimize', { state: { source: item.body } })
                        }
                      >
                        <Wand2 className="h-3.5 w-3.5" /> 送到优化
                      </button>
                      <button
                        type="button"
                        className={btnIcon}
                        onClick={() => {
                          setEditing(item)
                          setForm({
                            title: item.title,
                            body: item.body,
                            category: item.category ?? '',
                            tags: item.tags.join(', '),
                          })
                        }}
                      >
                        <Pencil className="h-3.5 w-3.5" /> 编辑
                      </button>
                      <button
                        type="button"
                        className={btnIcon}
                        onClick={async () => {
                          await updatePromptItem(item.id, { pinned: !item.pinned })
                          await queryClient.invalidateQueries({ queryKey: ['prompt-items'] })
                        }}
                      >
                        <Pin className="h-3.5 w-3.5" /> {item.pinned ? '取消置顶' : '置顶'}
                      </button>
                      <button
                        type="button"
                        className={cn(
                          btnIcon,
                          'border-destructive/40 text-destructive hover:bg-destructive/10'
                        )}
                        onClick={async () => {
                          await deletePromptItem(item.id)
                          await queryClient.invalidateQueries({ queryKey: ['prompt-items'] })
                          toast.success('已删除')
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5" /> 删除
                      </button>
                    </div>
                  </article>
                </li>
              ))
            )}
          </ul>
        </section>
      </div>

      <VariableFillDialog
        body={fillBody ?? ''}
        open={fillBody != null}
        onClose={() => setFillBody(null)}
        onFilled={(text) => void copyText(text)}
      />
    </div>
  )
}
