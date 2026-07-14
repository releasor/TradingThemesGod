/** Dashboard Zustand Store
 *
 * 管理看板页面的筛选和显示状态。
 * 支持状态持久化到 localStorage。
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface DashboardState {
  /** 主题数量限制 */
  limit: number
  /** 是否显示图表 */
  showCharts: boolean
  /** 是否显示统计 */
  showStats: boolean
  /** 设置主题数量限制 */
  setLimit: (limit: number) => void
  /** 切换图表显示 */
  toggleCharts: () => void
  /** 切换统计显示 */
  toggleStats: () => void
}

export const useDashboardStore = create<DashboardState>()(
  persist(
    (set) => ({
      limit: 20,
      showCharts: true,
      showStats: true,
      setLimit: (limit) => set({ limit }),
      toggleCharts: () => set((state) => ({ showCharts: !state.showCharts })),
      toggleStats: () => set((state) => ({ showStats: !state.showStats })),
    }),
    {
      name: 'dashboard-storage',
    }
  )
)
