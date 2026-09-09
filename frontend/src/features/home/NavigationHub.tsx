/** 登录后 TradingThemesGod 功能导航页 */

import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'
import { motion } from 'motion/react'
import { useMemo } from 'react'

import { AppCardNav, APP_CARD_NAV_ITEMS } from '@/components/AppCardNav'
import { GlowCard } from '@/components/GlowCard'
import RippleDistortion from '@/components/RippleDistortion'
import { useAuthStore } from '@/stores/auth'
import { useChartTheme } from '@/hooks/useChartTheme'
import { cn } from '@/lib/utils'
import { NAV_HUB_DESCRIPTIONS } from '@/features/home/navHub'

const HERO_IMAGE =
  'https://images.unsplash.com/photo-1782977389500-dd7adad33ebe?q=80&w=2400&auto=format&fit=crop'

const sectionMotion = {
  hidden: { opacity: 0, y: 12 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: 0.06 * i, duration: 0.35, ease: [0.22, 1, 0.36, 1] },
  }),
}

export function NavigationHub() {
  const username = useAuthStore((state) => state.user?.username)
  const { isDark } = useChartTheme()
  const hubSections = useMemo(
    () => APP_CARD_NAV_ITEMS.filter((section) => section.tone !== 'settings'),
    []
  )

  return (
    <div className="min-h-screen" data-testid="navigation-hub">
      <AppCardNav />

      <header className="relative mx-3 mb-10 overflow-hidden rounded-2xl border border-border/50 sm:mx-4 sm:mb-12 lg:mx-5 xl:mx-6">
        <div className="absolute inset-0" aria-hidden="true">
          <RippleDistortion
            src={HERO_IMAGE}
            brushSize={180}
            strength={0.22}
            swirl={0.85}
            rings={4}
            spread={5}
            fade={3.2}
            spacing={18}
            dispersion={0.08}
            glint={0.35}
            tint={isDark ? '#38bdf8' : '#1e3a8a'}
            tintAmount={isDark ? 0.18 : 0.14}
            grayscale
            highlightColor="#ffffff"
            trigger="both"
            clickStrength={2.2}
            quality="medium"
            className="h-full w-full"
          />
          <div
            className={cn(
              'pointer-events-none absolute inset-0',
              isDark
                ? 'bg-[radial-gradient(ellipse_at_center,hsl(var(--background)/0.55)_0%,hsl(var(--background)/0.78)_55%,hsl(var(--background)/0.88)_100%)]'
                : 'bg-[radial-gradient(ellipse_at_center,hsl(var(--background)/0.45)_0%,hsl(var(--background)/0.72)_55%,hsl(var(--background)/0.88)_100%)]'
            )}
          />
        </div>

        <div className="relative z-10 flex min-h-[28rem] items-center justify-center px-5 py-12 text-center sm:min-h-[32rem] sm:px-8 sm:py-16 lg:min-h-[36rem] lg:px-10">
          <div className="mx-auto max-w-2xl">
            <h1 className="text-4xl font-semibold tracking-tight text-foreground drop-shadow-sm sm:text-5xl lg:text-6xl">
              TradingThemesGod
            </h1>
            <p className="mx-auto mt-4 max-w-xl text-base text-muted-foreground sm:text-lg">
              {username ? `欢迎回来，${username}` : '欢迎回来'}
              。从下方入口进入题材看板或复盘研究。
            </p>
            <p className="mt-3">
              <Link
                to="/"
                className="text-sm text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline"
              >
                ← 返回项目入口
              </Link>
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl px-4 pb-16 sm:px-6 lg:px-8">
        <div className="space-y-12">
          {hubSections.map((section, sectionIndex) => (
            <motion.section
              key={section.label}
              custom={sectionIndex}
              variants={sectionMotion}
              initial="hidden"
              animate="show"
              aria-labelledby={`hub-section-${sectionIndex}`}
            >
              <h2
                id={`hub-section-${sectionIndex}`}
                className="mb-4 text-sm font-semibold uppercase tracking-[0.14em] text-muted-foreground"
              >
                {section.label}
              </h2>
              <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {section.links.map((link) => {
                  const description =
                    NAV_HUB_DESCRIPTIONS[link.href] || '打开该功能页面'
                  return (
                    <li key={`${section.label}-${link.href}`}>
                      <GlowCard className="h-full transition-transform duration-200 hover:-translate-y-0.5 active:translate-y-0">
                        <Link
                          to={link.href}
                          aria-label={link.ariaLabel}
                          className={cn(
                            'group flex h-full flex-col gap-3 p-4 sm:p-5',
                            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
                          )}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <span className="text-base font-semibold text-foreground">
                              {link.label}
                            </span>
                            <ArrowUpRight
                              className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-foreground group-active:scale-95"
                              aria-hidden
                            />
                          </div>
                          <p className="text-sm leading-relaxed text-muted-foreground">
                            {description}
                          </p>
                        </Link>
                      </GlowCard>
                    </li>
                  )
                })}
              </ul>
            </motion.section>
          ))}
        </div>
      </main>
    </div>
  )
}
