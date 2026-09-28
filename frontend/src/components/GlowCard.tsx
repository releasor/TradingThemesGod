/** Theme-aware BorderGlow wrapper for content cards */

import type { ReactNode } from 'react'
import { useChartTheme } from '@/hooks/useChartTheme'
import BorderGlow from '@/components/BorderGlow'
import { cn } from '@/lib/utils'

interface GlowCardProps {
  children: ReactNode
  className?: string
  /** Extra classes on the inner content shell */
  contentClassName?: string
  animated?: boolean
  /** Override card surface color used by the glow mask */
  backgroundColor?: string
  /** Slightly more sensitive edge tracking (e.g. compact nav cards) */
  edgeSensitivity?: number
  glowRadius?: number
  glowIntensity?: number
  fillOpacity?: number
}

const DARK_COLORS = ['#38bdf8', '#6366f1', '#818cf8']
const LIGHT_COLORS = ['#2563eb', '#1e3a8a', '#312e81']

export function GlowCard({
  children,
  className,
  contentClassName,
  animated = false,
  backgroundColor,
  edgeSensitivity = 24,
  glowRadius = 24,
  glowIntensity,
  fillOpacity,
}: GlowCardProps) {
  const { isDark } = useChartTheme()

  return (
    <BorderGlow
      className={cn(className)}
      edgeSensitivity={edgeSensitivity}
      glowColor={isDark ? '199 95 78' : '220 72 48'}
      backgroundColor={backgroundColor ?? 'hsl(var(--card))'}
      borderRadius={14}
      glowRadius={glowRadius}
      glowIntensity={glowIntensity ?? (isDark ? 1.35 : 0.85)}
      coneSpread={20}
      animated={animated}
      colors={isDark ? DARK_COLORS : LIGHT_COLORS}
      fillOpacity={fillOpacity ?? (isDark ? 0.5 : 0.3)}
    >
      <div className={cn('h-full w-full', contentClassName)}>{children}</div>
    </BorderGlow>
  )
}
