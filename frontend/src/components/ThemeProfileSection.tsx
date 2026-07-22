import { BookOpen, ExternalLink } from 'lucide-react'

import { cn } from '@/lib/utils'
import { GlowCard } from '@/components/GlowCard'
import type { ThemeProfile } from '@/types/theme'

interface ThemeProfileSectionProps {
  profile: ThemeProfile | null
  className?: string
}

export function ThemeProfileSection({ profile, className }: ThemeProfileSectionProps) {
  if (!profile)
    return (
      <section
        aria-labelledby="theme-profile-heading"
        className={cn(
          'rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground',
          className
        )}
      >
        <div className="flex items-center gap-3">
          <BookOpen className="h-5 w-5 text-primary" />
          <h2 id="theme-profile-heading" className="text-lg font-semibold text-foreground">
            题材详细介绍
          </h2>
        </div>
        <p className="mt-4">暂无详细介绍，可点击“刷新题材资料”获取。</p>
      </section>
    )
  const lists = [
    { title: '应用场景', values: profile.applications },
    { title: '主要催化', values: profile.catalysts },
    { title: '风险提示', values: profile.risks },
  ]
  return (
    <GlowCard className={className}>
      <section aria-labelledby="theme-profile-heading" className="p-5 sm:p-6">
        <div className="flex items-center gap-3">
          <BookOpen className="h-5 w-5 text-primary" />
          <div>
            <p className="text-xs uppercase tracking-widest text-muted-foreground">Research brief</p>
            <h2 id="theme-profile-heading" className="text-lg font-semibold">
              题材详细介绍
            </h2>
          </div>
        </div>
        <div className="mt-6 grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <div className="space-y-5">
            <div>
              <h3 className="text-sm font-semibold">概念定义</h3>
              <p className="mt-2 leading-7 text-muted-foreground">{profile.definition}</p>
            </div>
            <div>
              <h3 className="text-sm font-semibold">核心逻辑</h3>
              <p className="mt-2 leading-7 text-muted-foreground">{profile.core_logic}</p>
            </div>
          </div>
          <div className="space-y-4">
            {lists.map((item) => (
              <div key={item.title}>
                <h3 className="text-sm font-semibold">{item.title}</h3>
                <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                  {item.values.map((value) => (
                    <li key={value} className="border-l-2 border-border pl-3">
                      {value}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
        <footer className="mt-6 border-t border-border pt-4 text-xs text-muted-foreground">
          <span>更新于 {new Date(profile.generated_at).toLocaleString('zh-CN')}</span>
          <div className="mt-2 flex flex-wrap gap-3">
            {profile.sources.map((source) => (
              <a
                key={source.url}
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-foreground hover:underline"
              >
                {source.title}
                <ExternalLink className="h-3 w-3" />
              </a>
            ))}
          </div>
        </footer>
      </section>
    </GlowCard>
  )
}
