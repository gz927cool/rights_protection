import { create } from 'zustand'

interface UserState {
  userId: string | null
  phone: string | null
  name: string | null
  token: string | null
  setUser: (user: { id: string; phone: string; name?: string }) => void
  setToken: (token: string) => void
  logout: () => void
}

export const useUserStore = create<UserState>((set) => ({
  userId: null,
  phone: null,
  name: null,
  token: null,
  setUser: (user) => set({ userId: user.id, phone: user.phone, name: user.name || null }),
  setToken: (token) => set({ token }),
  logout: () => set({ userId: null, phone: null, name: null, token: null })
}))
