import { create } from 'zustand'

interface AppState {
  sessionId: string
  reviewResult: any
  loading: boolean
  activePage: string

  setSessionId: (id: string) => void
  setReviewResult: (data: any) => void
  setLoading: (value: boolean) => void
  setActivePage: (page: string) => void
}

export const useAppStore = create<AppState>((set) => ({
  sessionId: '',
  reviewResult: null,
  loading: false,
  activePage: 'dashboard',

  setSessionId: (id) =>
    set({ sessionId: id }),

  setReviewResult: (data) =>
    set({ reviewResult: data }),

  setLoading: (value) =>
    set({ loading: value }),

  setActivePage: (page) =>
    set({ activePage: page }),
}))