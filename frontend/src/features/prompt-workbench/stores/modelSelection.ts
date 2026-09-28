import { create } from 'zustand'

interface ModelSelectionState {
  providerId: number | null
  setProviderId: (id: number | null) => void
}

export const usePromptModelSelection = create<ModelSelectionState>((set) => ({
  providerId: null,
  setProviderId: (providerId) => set({ providerId }),
}))
