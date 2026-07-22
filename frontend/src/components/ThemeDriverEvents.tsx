import { ExternalLink, Radio } from 'lucide-react'

import { cn } from '@/lib/utils'
import type { ThemeDriverEvent } from '@/types/theme'

interface ThemeDriverEventsProps {
  events: ThemeDriverEvent[]
  className?: string
}

export function ThemeDriverEvents({ events, className }: ThemeDriverEventsProps) {
  return (
    <section aria-labelledby="driver-events-heading" className={cn('py-2', className)}>
      <div className="mb-5 flex items-center gap-3">
        <Radio className="h-5 w-5 text-primary" />
        <div>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Catalyst tape</p>
          <h2 id="driver-events-heading" className="text-lg font-semibold">
            最近驱动事件
          </h2>
        </div>
      </div>
      {events.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground">
          返30 天暂未发现可靠驱动事件
        </p>
      ) : (
        <ol className="relative border-l border-border pl-5">
          {events.slice(0, 5).map((event) => (
            <li key={event.id} data-testid="driver-event" className="relative pb-6 last:pb-0">
              <span className="absolute -left-[1.55rem] top-1.5 h-2 w-2 rounded-full bg-primary ring-4 ring-background" />
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <time className="text-xs tabular-nums text-muted-foreground">
                  {new Date(event.published_at).toLocaleString('zh-CN')}
                </time>
                <span className="text-xs text-muted-foreground">
                  相关度{event.relevance_score}
                </span>
              </div>
              <h3 className="mt-1 font-semibold leading-6">{event.title}</h3>
              <p className="mt-1 break-words text-sm leading-6 text-muted-foreground">
                {event.summary}
              </p>
              <a
                href={event.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-flex min-h-0 items-center gap-1 break-all text-xs text-foreground hover:underline"
              >
                {event.source}
                <ExternalLink className="h-3 w-3 shrink-0" />
              </a>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
