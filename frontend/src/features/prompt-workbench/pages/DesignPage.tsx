import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useToastContext } from '@/App'
import { designPrompt } from '@/features/prompt-workbench/api/optimize'
import { createPromptItem } from '@/features/prompt-workbench/api/library'
import { usePromptModelSelection } from '@/features/prompt-workbench/stores/modelSelection'
import { cn } from '@/lib/utils'

const panel = 'flex min-h-0 flex-col rounded-xl border border-border bg-card'
const field = 'w-full rounded-md border border-input bg-background px-3 text-sm'
const btn =
  'inline-flex h-9 shrink-0 items-center justify-center rounded-md px-3 text-sm transition-colors'
const btnPrimary = cn(btn, 'bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50')
const btnGhost = cn(btn, 'border border-input hover:bg-accent disabled:opacity-50')

export function DesignPage() {
  const toast = useToastContext()
  const navigate = useNavigate()
  const providerId = usePromptModelSelection((s) => s.providerId)
  const [goal, setGoal] = useState('')
  const [notes, setNotes] = useState('')
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(false)

  async function run() {
    if (!goal.trim()) {
      toast.warning('请填写任务目标')
      return
    }
    setLoading(true)
    try {
      const res = await designPrompt({
        goal,
        notes: notes || undefined,
        provider_id: providerId,
      })
      setResult(res.result)
      toast.success('已生成')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '生成失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)] gap-3 overflow-y-auto lg:overflow-hidden"
      data-testid="prompt-design-page"
    >
      <div className="shrink-0">
        <h2 className="text-lg font-semibold tracking-tight">设计 Prompt</h2>
        <p className="text-sm text-muted-foreground">从任务目标写出可复用 Prompt</p>
      </div>

      <div className="grid min-h-0 gap-3 lg:grid-cols-2 lg:overflow-hidden">
        <section className={cn(panel, 'min-h-[18rem] gap-3 p-4 lg:min-h-0')}>
          <label className="flex min-h-0 flex-[1.2] flex-col text-sm">
            <span className="mb-1.5 shrink-0 text-muted-foreground">任务目标</span>
            <textarea
              className={cn(field, 'min-h-[6rem] flex-1 resize-none py-2')}
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
            />
          </label>
          <label className="flex min-h-0 flex-1 flex-col text-sm">
            <span className="mb-1.5 shrink-0 text-muted-foreground">补充约束（可选）</span>
            <textarea
              className={cn(field, 'min-h-[4rem] flex-1 resize-none py-2')}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="受众、语气、输出格式等"
            />
          </label>
          <button
            type="button"
            className={cn(btnPrimary, 'w-full sm:w-auto')}
            disabled={loading}
            onClick={() => void run()}
          >
            {loading ? '生成中…' : '生成 Prompt'}
          </button>
        </section>

        <section className={cn(panel, 'min-h-[16rem] gap-3 p-4 lg:min-h-0')}>
          <h3 className="shrink-0 text-sm font-medium text-muted-foreground">生成结果</h3>
          <textarea
            className={cn(field, 'min-h-[8rem] flex-1 resize-none py-2 lg:min-h-0')}
            value={result}
            onChange={(e) => setResult(e.target.value)}
            placeholder="生成结果将显示在这里，可直接编辑"
          />
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={btnGhost}
              disabled={!result}
              onClick={async () => {
                await navigator.clipboard.writeText(result)
                toast.success('已复制')
              }}
            >
              复制
            </button>
            <button
              type="button"
              className={btnGhost}
              disabled={!result}
              onClick={async () => {
                await createPromptItem({
                  title: `设计 ${new Date().toLocaleString()}`,
                  body: result,
                })
                toast.success('已存入库')
                navigate('/prompt/library')
              }}
            >
              保存到库
            </button>
            <button
              type="button"
              className={btnGhost}
              disabled={!result}
              onClick={() =>
                navigate('/prompt/optimize', { state: { source: result } })
              }
            >
              送到优化
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}
