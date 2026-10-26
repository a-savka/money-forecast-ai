import { create } from 'zustand'

import type { Alert } from '@/api/types'

interface ToastState {
  toasts: Alert[]
  push: (a: Alert) => void
  dismiss: (id: string) => void
}

export const useToasts = create<ToastState>()((set) => ({
  toasts: [],
  push: (a) => {
    set((s) => ({ toasts: [...s.toasts.filter((t) => t.id !== a.id), a].slice(-3) }))
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== a.id) })), 8000)
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))
