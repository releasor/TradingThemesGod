/** Dashboard Zustand Store
 *
 * 管理看板页面的筛选和显示状态。
 */

import { create } from 'zustand'

interface DashboardState {
  /** 主题数量限制 */
  limit: number
  /** 设置主题数量限制 */
  setLimit: (limit: number) => void
}

export const useDashboardStore = create<DashboardState>((set) => ({
  limit: 20,
  setLimit: (limit) => set({ limit }),
}))
