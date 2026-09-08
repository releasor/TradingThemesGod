/** 全局 GlowCursor 背景 — 固定全屏，窗口级追踪指针，不阻挡交互 */

import { useEffect, useState } from 'react'
import { useChartTheme } from '@/hooks/useChartTheme'
import GlowCursor from '@/components/GlowCursor'

/** 暗色：与 SideRays 冷光一致 */
const DARK_COLOR = '#38bdf8'
const DARK_SECONDARY = '#818cf8'

/** 亮色：深蓝，白底可见且不过分刺眼 */
const LIGHT_COLOR = '#1e3a8a'
const LIGHT_SECONDARY = '#312e81'

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function GlobalGlowCursorBackground() {
  const { isDark } = useChartTheme()
  const [reducedMotion, setReducedMotion] = useState(prefersReducedMotion)

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = () => setReducedMotion(media.matches)
    onChange()
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])

  if (reducedMotion) return null

  return (
    <div
      className="pointer-events-none fixed inset-0 z-[1] overflow-hidden"
      aria-hidden="true"
    >
      <GlowCursor
        trackWindow
        color={isDark ? DARK_COLOR : LIGHT_COLOR}
        secondaryColor={isDark ? DARK_SECONDARY : LIGHT_SECONDARY}
        trailLength={36}
        trailWidth={isDark ? 10 : 8}
        trailTaper={0.85}
        followSpeed={0.18}
        glowIntensity={isDark ? 1.7 : 1.35}
        glowSpread={isDark ? 1.35 : 1.1}
        hotspot={0.55}
        brightness={isDark ? 1.15 : 0.95}
        opacity={isDark ? 0.7 : 0.55}
        pulseSpeed={0.9}
        noiseStrength={0.03}
        idleFade
        idleTimeout={900}
        fadeDuration={1000}
        blendMode="screen"
        maxDevicePixelRatio={1.5}
        enabled
        className="h-full w-full"
      />
    </div>
  )
}
