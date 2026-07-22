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
}

const DARK_COLORS = ['#38bdf8', '#6366f1', '#818cf8']
const LIGHT_COLORS = ['#2563eb', '#1e3a8a', '#312e81']

export function GlowCard({
  children,
  className,
  contentClassName,
  animated = false,
}: GlowCardProps) {
  const { isDark } = useChartTheme()

  return (
    <BorderGlow
      className={cn(className)}
      edgeSensitivity={28}
      glowColor={isDark ? '200 90 70' : '220 70 45'}
      backgroundColor={isDark ? 'hsl(222.2 84% 4.9%)' : 'hsl(0 0% 100%)'}
      borderRadius={12}
      glowRadius={24}
      glowIntensity={isDark ? 1 : 0.75}
      coneSpread={25}
      animated={animated}
      colors={isDark ? DARK_COLORS : LIGHT_COLORS}
      fillOpacity={isDark ? 0.4 : 0.28}
    >
      <div className={cn('h-full w-full', contentClassName)}>{children}</div>
    </BorderGlow>
  )
}
