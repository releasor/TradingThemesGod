/** 全局 SideRays 背景 — 固定全屏，随亮/暗主题调节强度 */

import { useChartTheme } from '@/hooks/useChartTheme'
import SideRays from '@/components/SideRays'

/** 暗色模式：亮冷光 */
const DARK_RAY_1 = '#38bdf8'
const DARK_RAY_2 = '#6366f1'

/** 亮色模式：深蓝紫光，在白底上可见 */
const LIGHT_RAY_1 = '#1e3a8a'
const LIGHT_RAY_2 = '#312e81'

export function GlobalSideRaysBackground() {
  const { isDark } = useChartTheme()

  return (
    <div
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden"
      aria-hidden="true"
    >
      <SideRays
        speed={2.5}
        rayColor1={isDark ? DARK_RAY_1 : LIGHT_RAY_1}
        rayColor2={isDark ? DARK_RAY_2 : LIGHT_RAY_2}
        intensity={isDark ? 1.8 : 1.6}
        spread={2}
        origin="top-right"
        tilt={0}
        saturation={isDark ? 1.4 : 1.2}
        blend={0.75}
        falloff={1.6}
        opacity={isDark ? 0.65 : 0.55}
      />
    </div>
  )
}
