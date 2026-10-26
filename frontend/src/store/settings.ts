import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SettingsState {
  /** Активная стратегия прогноза (переключается на экране «Эксперименты») */
  strategy: string
  setStrategy: (s: string) => void
  /** Формулировки советов: шаблоны правил или переписанные LLM */
  recommendationsMode: 'rules' | 'llm'
  setRecommendationsMode: (m: 'rules' | 'llm') => void
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      strategy: 'statistical',
      setStrategy: (strategy) => set({ strategy }),
      recommendationsMode: 'rules',
      setRecommendationsMode: (recommendationsMode) => set({ recommendationsMode }),
    }),
    { name: 'mf-settings' },
  ),
)
