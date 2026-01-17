import axios from 'axios'
import type { AxiosRequestConfig } from 'axios'
import { getKeycloak, keycloakLogout } from './keycloak'
import { useAuthStore } from './store'
import { notifyError } from './notifications'

interface RetriableRequest extends AxiosRequestConfig {
  _retry?: boolean
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || ''

export const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use(async (config) => {
  // Try Keycloak token first
  if (typeof window !== 'undefined') {
    try {
      const kc = getKeycloak()
      if (kc.authenticated && kc.token) {
        // Refresh token if needed
        await kc.updateToken(30)
        config.headers.Authorization = `Bearer ${kc.token}`
        return config
      }
    } catch (e) {
      // Keycloak not initialized or not authenticated
    }
  }
  
  // Fall back to stored token
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle token refresh on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as RetriableRequest
    const status = error.response?.status

    const handleAuthFailure = () => {
      const { logout, authSource } = useAuthStore.getState()
      logout()
      if (typeof window !== 'undefined') {
        notifyError('Your session expired. Please sign in again.')
        if (authSource === 'keycloak') {
          try {
            keycloakLogout(window.location.origin + '/login')
            return
          } catch {
            // If Keycloak logout fails, fall back to redirect
          }
        }
        window.location.href = '/login'
      }
    }

    if (status === 401 && !originalRequest?._retry) {
      originalRequest._retry = true

      // Try Keycloak refresh first
      if (typeof window !== 'undefined') {
        try {
          const kc = getKeycloak()
          if (kc.authenticated) {
            const refreshed = await kc.updateToken(-1) // Force refresh
            if (refreshed && kc.token) {
              originalRequest.headers = {
                ...originalRequest.headers,
                Authorization: `Bearer ${kc.token}`,
              }
              return api(originalRequest)
            }
          }
        } catch {
          // Keycloak refresh failed
        }
      }

      // Try legacy refresh token
      const refreshToken = typeof window !== 'undefined' ? localStorage.getItem('refresh_token') : null
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          })

          const { access_token, refresh_token } = response.data
          localStorage.setItem('access_token', access_token)
          localStorage.setItem('refresh_token', refresh_token)

          originalRequest.headers = {
            ...originalRequest.headers,
            Authorization: `Bearer ${access_token}`,
          }
          return api(originalRequest)
        } catch {
          // Legacy refresh failed
        }
      }

      handleAuthFailure()
      return Promise.reject(error)
    }

    if (status && status >= 400) {
      const friendlyMessage =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Something went wrong. Please try again.'
      notifyError(friendlyMessage)
    }

    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password })
    return response.data
  },
  logout: async () => {
    const response = await api.post('/auth/logout')
    return response.data
  },
  me: async () => {
    const response = await api.get('/auth/me')
    return response.data
  },
  getKeycloakConfig: async () => {
    const response = await api.get('/auth/keycloak/config')
    return response.data
  },
  exchangeKeycloakCode: async (code: string, redirectUri: string) => {
    const response = await api.post('/auth/keycloak/token', { code, redirect_uri: redirectUri })
    return response.data
  },
}

// Companies API
export const companiesApi = {
  list: async () => {
    const response = await api.get('/companies')
    return response.data
  },
  create: async (data: { name: string; domain: string; logo_url?: string }) => {
    const response = await api.post('/companies', data)
    return response.data
  },
  get: async (id: string) => {
    const response = await api.get(`/companies/${id}`)
    return response.data
  },
  update: async (id: string, data: any) => {
    const response = await api.put(`/companies/${id}`, data)
    return response.data
  },
  delete: async (id: string) => {
    const response = await api.delete(`/companies/${id}`)
    return response.data
  },
  stats: async (id: string) => {
    const response = await api.get(`/companies/${id}/stats`)
    return response.data
  },
}

// Users API
export const usersApi = {
  list: async (page = 1, pageSize = 20, companyId?: string) => {
    let url = `/users?page=${page}&page_size=${pageSize}`
    if (companyId) {
      url += `&company_id=${companyId}`
    }
    const response = await api.get(url)
    return response.data
  },
  create: async (data: any) => {
    const response = await api.post('/users', data)
    return response.data
  },
  get: async (id: string) => {
    const response = await api.get(`/users/${id}`)
    return response.data
  },
  update: async (id: string, data: any) => {
    const response = await api.put(`/users/${id}`, data)
    return response.data
  },
  delete: async (id: string) => {
    const response = await api.delete(`/users/${id}`)
    return response.data
  },
  import: async (csvData: string, companyId?: string) => {
    const response = await api.post('/users/import', { 
      csv_data: csvData,
      ...(companyId && { company_id: companyId })
    })
    return response.data
  },
}

// Campaigns API
export const campaignsApi = {
  list: async () => {
    const response = await api.get('/campaigns')
    return response.data
  },
  create: async (data: any) => {
    const response = await api.post('/campaigns', data)
    return response.data
  },
  get: async (id: string) => {
    const response = await api.get(`/campaigns/${id}`)
    return response.data
  },
  update: async (id: string, data: any) => {
    const response = await api.put(`/campaigns/${id}`, data)
    return response.data
  },
  delete: async (id: string) => {
    const response = await api.delete(`/campaigns/${id}`)
    return response.data
  },
  schedule: async (id: string, scheduledAt: string) => {
    const response = await api.post(`/campaigns/${id}/schedule`, { scheduled_at: scheduledAt })
    return response.data
  },
  start: async (id: string) => {
    const response = await api.post(`/campaigns/${id}/start`)
    return response.data
  },
  stop: async (id: string) => {
    const response = await api.post(`/campaigns/${id}/stop`)
    return response.data
  },
  stats: async (id: string) => {
    const response = await api.get(`/campaigns/${id}/stats`)
    return response.data
  },
  targets: async (id: string) => {
    const response = await api.get(`/campaigns/${id}/targets`)
    return response.data
  },
}

// Templates API
export const templatesApi = {
  list: async () => {
    const response = await api.get('/templates')
    return response.data
  },
  create: async (data: any) => {
    const response = await api.post('/templates', data)
    return response.data
  },
  get: async (id: string) => {
    const response = await api.get(`/templates/${id}`)
    return response.data
  },
  update: async (id: string, data: any) => {
    const response = await api.put(`/templates/${id}`, data)
    return response.data
  },
  delete: async (id: string) => {
    const response = await api.delete(`/templates/${id}`)
    return response.data
  },
  preview: async (id: string, data?: any) => {
    const response = await api.post(`/templates/${id}/preview`, data || {})
    return response.data
  },
}

// Dashboard API
export const dashboardApi = {
  myCampaigns: async () => {
    const response = await api.get('/dashboard/my-campaigns')
    return response.data
  },
  myResults: async () => {
    const response = await api.get('/dashboard/my-results')
    return response.data
  },
  myStats: async () => {
    const response = await api.get('/dashboard/stats')
    return response.data
  },
  recommendations: async () => {
    const response = await api.get('/dashboard/recommendations')
    return response.data
  },
  training: async () => {
    const response = await api.get('/dashboard/training')
    return response.data
  },
  completeTraining: async (id: string) => {
    const response = await api.post(`/dashboard/training/${id}/complete`)
    return response.data
  },
}
