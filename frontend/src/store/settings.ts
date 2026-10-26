import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SettingsState {
  /** Активная стратегия прогноза (переключается на экране «Эксперименты») */
  strategy: string
  setStrategy: (s: string) => void
  /** Формулировки советов: шаблоны правил или переписанные LLM */
  recommendationsMode: 'rules' | 'llm'
  setRecommendationsMode: (m: 'rules' | 'llm') => void
  /** Уведомления о риске разрыва, лимитах и платежах */
  notificationsEnabled: boolean
  setNotificationsEnabled: (v: boolean) => void
  /** Цель из онбординга: no_gap | control | save */
  goal: string | null
  setGoal: (g: string) => void
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      strategy: 'statistical',
      setStrategy: (strategy) => set({ strategy }),
      recommendationsMode: 'rules',
      setRecommendationsMode: (recommendationsMode) => set({ recommendationsMode }),
      notificationsEnabled: true,
      setNotificationsEnabled: (notificationsEnabled) => set({ notificationsEnabled }),
      goal: null,
      setGoal: (goal) => set({ goal }),
    }),
    { name: 'mf-settings' },
  ),
)
