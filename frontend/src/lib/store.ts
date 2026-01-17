import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: 'SUPER_ADMIN' | 'ADMIN' | 'USER'
  company_id?: string
  is_active: boolean
  auth_source?: 'keycloak' | 'database'
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  accessToken: string | null
  refreshToken: string | null
  authSource: 'keycloak' | 'legacy' | null
  setAuth: (user: User, accessToken: string, refreshToken: string, source?: 'keycloak' | 'legacy') => void
  setKeycloakAuth: (user: User, accessToken: string, refreshToken: string) => void
  updateTokens: (accessToken: string, refreshToken: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      accessToken: null,
      refreshToken: null,
      authSource: null,
      setAuth: (user, accessToken, refreshToken, source = 'legacy') => {
        localStorage.setItem('access_token', accessToken)
        localStorage.setItem('refresh_token', refreshToken)
        set({
          user,
          isAuthenticated: true,
          accessToken,
          refreshToken,
          authSource: source,
        })
      },
      setKeycloakAuth: (user, accessToken, refreshToken) => {
        localStorage.setItem('access_token', accessToken)
        localStorage.setItem('refresh_token', refreshToken)
        set({
          user,
          isAuthenticated: true,
          accessToken,
          refreshToken,
          authSource: 'keycloak',
        })
      },
      updateTokens: (accessToken, refreshToken) => {
        localStorage.setItem('access_token', accessToken)
        localStorage.setItem('refresh_token', refreshToken)
        set({
          accessToken,
          refreshToken,
        })
      },
      logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        set({
          user: null,
          isAuthenticated: false,
          accessToken: null,
          refreshToken: null,
          authSource: null,
        })
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        authSource: state.authSource,
      }),
    }
  )
)

// UI State
interface UIState {
  sidebarOpen: boolean
  toggleSidebar: () => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
}))
