import { useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { gsap } from 'gsap'
import { ArrowUpRight } from 'lucide-react'
import { GlowCard } from '@/components/GlowCard'
import { useChartTheme } from '@/hooks/useChartTheme'
import './CardNav.css'

export type CardNavLink = {
  label: string
  href: string
  ariaLabel: string
}

export type CardNavTone = 'dashboard' | 'analysis' | 'settings' | 'review'

const NAV_CARD_SURFACE: Record<'light' | 'dark', Record<CardNavTone, string>> = {
  light: {
    dashboard: 'hsl(222 28% 94%)',
    analysis: 'hsl(210 40% 94%)',
    review: 'hsl(160 18% 93%)',
    settings: 'hsl(40 24% 94%)',
  },
  dark: {
    dashboard: 'hsl(222 28% 14%)',
    analysis: 'hsl(210 32% 15%)',
    review: 'hsl(165 14% 14%)',
    settings: 'hsl(36 18% 14%)',
  },
}

export type CardNavItem = {
  label: string
  links: CardNavLink[]
  /** Theme-aware surface tone; preferred over fixed bg/text colors */
  tone?: CardNavTone
  bgColor?: string
  textColor?: string
}

export interface CardNavProps {
  logo?: string
  logoAlt?: string
  logoElement?: ReactNode
  items: CardNavItem[]
  className?: string
  ease?: string
  baseColor?: string
  menuColor?: string
  buttonBgColor?: string
  buttonTextColor?: string
  ctaLabel?: string
  ctaHref?: string
  logoHref?: string
}

function BrandLogoMark({ title }: { title: string }) {
  return (
    <svg
      className="card-nav-logo-mark"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 180 36"
      fill="none"
      role="img"
      aria-label={title}
    >
      <title>{title}</title>
      <rect className="card-nav-logo-badge" x="0" y="4" width="28" height="28" rx="8" />
      <path
        className="card-nav-logo-badge-stroke"
        d="M8 12h12M14 12v12"
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <text
        x="40"
        y="24"
        fill="currentColor"
        fontFamily="Segoe UI, system-ui, sans-serif"
        fontSize="16"
        fontWeight="700"
      >
        TradingThemes
      </text>
    </svg>
  )
}

export function CardNav({
  logo,
  logoAlt = 'Logo',
  logoElement,
  items,
  className = '',
  ease = 'power3.out',
  baseColor,
  menuColor,
  buttonBgColor,
  buttonTextColor,
  ctaLabel,
  ctaHref = '/',
  logoHref = '/',
}: CardNavProps) {
  const [isHamburgerOpen, setIsHamburgerOpen] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [isAnimating, setIsAnimating] = useState(false)
  const navRef = useRef<HTMLElement | null>(null)
  const cardsRef = useRef<HTMLDivElement[]>([])
  const tlRef = useRef<gsap.core.Timeline | null>(null)
  const { isDark } = useChartTheme()
  const surfaceKey = isDark ? 'dark' : 'light'

  const calculateHeight = () => {
    const navEl = navRef.current
    if (!navEl) return 260

    const isMobile = window.matchMedia('(max-width: 768px)').matches
    if (isMobile) {
      const contentEl = navEl.querySelector('.card-nav-content') as HTMLElement | null
      if (contentEl) {
        const wasVisible = contentEl.style.visibility
        const wasPointerEvents = contentEl.style.pointerEvents
        const wasPosition = contentEl.style.position
        const wasHeight = contentEl.style.height

        contentEl.style.visibility = 'visible'
        contentEl.style.pointerEvents = 'auto'
        contentEl.style.position = 'static'
        contentEl.style.height = 'auto'

        contentEl.offsetHeight

        const topBar = 60
        const padding = 16
        const contentHeight = contentEl.scrollHeight

        contentEl.style.visibility = wasVisible
        contentEl.style.pointerEvents = wasPointerEvents
        contentEl.style.position = wasPosition
        contentEl.style.height = wasHeight

        return topBar + contentHeight + padding
      }
    }
    return 260
  }

  const createTimeline = () => {
    const navEl = navRef.current
    if (!navEl) return null

    gsap.set(navEl, { height: 60 })
    gsap.set(cardsRef.current, { y: 50, autoAlpha: 0 })

    const tl = gsap.timeline({
      paused: true,
      onComplete: () => {
        setIsAnimating(false)
        // Drop opacity stacking context so mix-blend edge light can render
        gsap.set(cardsRef.current, { clearProps: 'opacity,visibility' })
      },
      onReverseComplete: () => {
        setIsAnimating(false)
        setIsExpanded(false)
      },
    })

    tl.to(navEl, {
      height: calculateHeight,
      duration: 0.4,
      ease,
    })

    tl.to(
      cardsRef.current,
      { y: 0, autoAlpha: 1, duration: 0.4, ease, stagger: 0.08 },
      '-=0.1'
    )

    return tl
  }

  useLayoutEffect(() => {
    const tl = createTimeline()
    tlRef.current = tl

    return () => {
      tl?.kill()
      tlRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- recreate when menu content/easing changes
  }, [ease, items])

  useLayoutEffect(() => {
    const handleResize = () => {
      if (!tlRef.current) return

      if (isExpanded) {
        const newHeight = calculateHeight()
        gsap.set(navRef.current, { height: newHeight })

        tlRef.current.kill()
        const newTl = createTimeline()
        if (newTl) {
          newTl.progress(1, false)
          gsap.set(cardsRef.current, { clearProps: 'opacity,visibility' })
          setIsAnimating(false)
          tlRef.current = newTl
        }
      } else {
        tlRef.current.kill()
        const newTl = createTimeline()
        if (newTl) {
          tlRef.current = newTl
        }
      }
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isExpanded])

  const closeMenu = () => {
    const tl = tlRef.current
    if (!tl || !isExpanded) return
    setIsHamburgerOpen(false)
    setIsAnimating(true)
    tl.reverse()
  }

  const toggleMenu = () => {
    const tl = tlRef.current
    if (!tl) return
    if (!isExpanded) {
      setIsHamburgerOpen(true)
      setIsExpanded(true)
      setIsAnimating(true)
      tl.play(0)
    } else {
      closeMenu()
    }
  }

  const setCardRef = (i: number) => (el: HTMLDivElement | null) => {
    if (el) cardsRef.current[i] = el
  }

  const resolvedLogo =
    logoElement ??
    (logo ? (
      <img src={logo} alt={logoAlt} className="logo" />
    ) : (
      <BrandLogoMark title={logoAlt} />
    ))

  return (
    <div className={`card-nav-container ${className}`.trim()}>
      <GlowCard
        className="card-nav-shell-glow"
        contentClassName="card-nav-shell-inner h-auto"
        backgroundColor={baseColor ?? 'hsl(var(--card))'}
      >
        <nav
          ref={navRef}
          className={`card-nav ${isExpanded ? 'open' : ''} ${isAnimating ? 'is-animating' : ''}`.trim()}
        >
          <div className="card-nav-top">
            <div
              className={`hamburger-menu ${isHamburgerOpen ? 'open' : ''}`}
              onClick={toggleMenu}
              onKeyDown={(e: KeyboardEvent<HTMLDivElement>) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  toggleMenu()
                }
              }}
              role="button"
              aria-label={isExpanded ? '关闭菜单' : '打开菜单'}
              aria-expanded={isExpanded}
              tabIndex={0}
              style={menuColor ? { color: menuColor } : undefined}
            >
              <div className="hamburger-line" />
              <div className="hamburger-line" />
            </div>

            <div className="logo-container">
              <Link to={logoHref} onClick={closeMenu} aria-label="返回首页">
                {resolvedLogo}
              </Link>
            </div>

            {ctaLabel ? (
              <Link
                to={ctaHref}
                className="card-nav-cta-button"
                style={{
                  ...(buttonBgColor ? { backgroundColor: buttonBgColor } : {}),
                  ...(buttonTextColor ? { color: buttonTextColor } : {}),
                }}
                onClick={closeMenu}
              >
                {ctaLabel}
              </Link>
            ) : (
              <span className="card-nav-cta-spacer" aria-hidden="true" />
            )}
          </div>

          <div className="card-nav-content" aria-hidden={!isExpanded}>
            {(items || []).slice(0, 4).map((item, idx) => {
              const toneBg =
                item.tone != null
                  ? NAV_CARD_SURFACE[surfaceKey][item.tone]
                  : item.bgColor
              return (
                <div
                  key={`${item.label}-${idx}`}
                  className="nav-card-glow-wrap"
                  ref={setCardRef(idx)}
                >
                  <GlowCard
                    className="nav-card-glow"
                    contentClassName="h-full"
                    backgroundColor={toneBg}
                    edgeSensitivity={22}
                    glowRadius={20}
                    glowIntensity={isDark ? 1.1 : 0.9}
                    fillOpacity={isDark ? 0.5 : 0.35}
                  >
                    <div
                      className="nav-card"
                      data-tone={item.tone}
                      style={
                        item.tone
                          ? undefined
                          : { backgroundColor: item.bgColor, color: item.textColor }
                      }
                    >
                      <div className="nav-card-label">{item.label}</div>
                      <div className="nav-card-links">
                        {item.links?.map((lnk, i) => (
                          <Link
                            key={`${lnk.label}-${i}`}
                            className="nav-card-link"
                            to={lnk.href}
                            aria-label={lnk.ariaLabel}
                            onClick={closeMenu}
                          >
                            <ArrowUpRight className="nav-card-link-icon" aria-hidden="true" />
                            {lnk.label}
                          </Link>
                        ))}
                      </div>
                    </div>
                  </GlowCard>
                </div>
              )
            })}
          </div>
        </nav>
      </GlowCard>
    </div>
  )
}

export default CardNav
