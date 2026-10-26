import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import type { components } from '@/api/schema'

export type User = components['schemas']['UserOut']

interface SessionState {
  token: string | null
  user: User | null
  setSession: (token: string, user: User) => void
  setUser: (user: User) => void
  logout: () => void
}

export const useSession = create<SessionState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      setSession: (token, user) => set({ token, user }),
      setUser: (user) => set({ user }),
      logout: () => set({ token: null, user: null }),
    }),
    { name: 'mf-session' },
  ),
)
