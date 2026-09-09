/** 项目级导航页 — 独立于 TradingThemesGod 内部导航 */

import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'
import { motion } from 'motion/react'

import { GlowCard } from '@/components/GlowCard'
import { ThemeToggle } from '@/components/ThemeToggle'
import { cn } from '@/lib/utils'
import { PROJECT_ENTRIES } from '@/features/launch/projectEntries'

const cardMotion = {
  hidden: { opacity: 0, y: 16 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: 0.08 * i, duration: 0.4, ease: [0.22, 1, 0.36, 1] },
  }),
}

export function ProjectLaunchPage() {
  return (
    <div
      className="relative min-h-screen overflow-hidden"
      data-testid="project-launch-page"
    >
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,hsl(var(--primary)/0.12),transparent_55%),radial-gradient(ellipse_at_bottom_right,hsl(210_80%_50%/0.08),transparent_45%)]"
        aria-hidden
      />

      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-5xl flex-col px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-auto flex items-center justify-between gap-4 pb-10">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
              Workspace
            </p>
            <p className="mt-1 text-sm text-muted-foreground">选择要进入的应用</p>
          </div>
          <ThemeToggle />
        </header>

        <main className="flex flex-1 flex-col justify-center pb-16 pt-4">
          <div className="mb-10 max-w-2xl">
            <h1 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
              项目入口
            </h1>
            <p className="mt-3 text-base text-muted-foreground sm:text-lg">
              这里只做应用跳转。TradingThemesGod 的功能导航在进入后再展开。
            </p>
          </div>

          <ul className="grid gap-4 sm:grid-cols-2">
            {PROJECT_ENTRIES.map((entry, index) => (
              <motion.li
                key={entry.id}
                custom={index}
                variants={cardMotion}
                initial="hidden"
                animate="show"
              >
                <GlowCard className="h-full transition-transform duration-200 hover:-translate-y-1 active:translate-y-0">
                  <Link
                    to={entry.to}
                    aria-label={entry.ariaLabel}
                    className={cn(
                      'group flex h-full min-h-[11rem] flex-col gap-4 p-5 sm:min-h-[12.5rem] sm:p-6',
                      'rounded-[inherit] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                    )}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-2">
                        <span className="inline-flex rounded-full border border-border/70 bg-muted/40 px-2.5 py-0.5 text-xs text-muted-foreground">
                          {entry.badge}
                        </span>
                        <h2 className="text-xl font-semibold tracking-tight text-foreground sm:text-2xl">
                          {entry.name}
                        </h2>
                      </div>
                      <ArrowUpRight
                        className="mt-1 h-5 w-5 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-foreground group-active:scale-95"
                        aria-hidden
                      />
                    </div>
                    <p className="text-sm leading-relaxed text-muted-foreground sm:text-base">
                      {entry.description}
                    </p>
                    <span className="mt-auto text-sm font-medium text-foreground/80 transition-colors group-hover:text-foreground">
                      进入 →
                    </span>
                  </Link>
                </GlowCard>
              </motion.li>
            ))}
          </ul>
        </main>
      </div>
    </div>
  )
}
