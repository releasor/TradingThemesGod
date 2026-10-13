import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface OsModelSelectionState {
  providerId: number | null
  setProviderId: (id: number | null) => void
}

export const useOsModelSelection = create<OsModelSelectionState>()(
  persist(
    (set) => ({
      providerId: null,
      setProviderId: (providerId) => set({ providerId }),
    }),
    { name: 'os-model-selection' }
  )
)
