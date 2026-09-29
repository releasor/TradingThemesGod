import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ModelSelectionState {
  providerId: number | null
  setProviderId: (id: number | null) => void
}

export const usePromptModelSelection = create<ModelSelectionState>()(
  persist(
    (set) => ({
      providerId: null,
      setProviderId: (providerId) => set({ providerId }),
    }),
    { name: 'prompt-model-selection' }
  )
)
