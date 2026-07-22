import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface NewsChannelState {
  disabledSources: string[]
  isSourceEnabled: (source: string) => boolean
  toggleSource: (source: string) => void
}

export const useNewsChannelStore = create<NewsChannelState>()(
  persist(
    (set, get) => ({
      disabledSources: [],
      isSourceEnabled: (source) => !get().disabledSources.includes(source),
      toggleSource: (source) =>
        set((state) => ({
          disabledSources: state.disabledSources.includes(source)
            ? state.disabledSources.filter((item) => item !== source)
            : [...state.disabledSources, source],
        })),
    }),
    {
      name: 'news-channel-settings',
      version: 1,
      partialize: (state) => ({ disabledSources: state.disabledSources }),
    }
  )
)
