import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SettingsState {
  /** Активная стратегия прогноза (переключается на экране «Эксперименты») */
  strategy: string
  setStrategy: (s: string) => void
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      strategy: 'statistical',
      setStrategy: (strategy) => set({ strategy }),
    }),
    { name: 'mf-settings' },
  ),
)
