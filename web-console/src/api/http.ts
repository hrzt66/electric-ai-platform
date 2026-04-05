import axios from 'axios'

import { useAuthStore } from '../stores/auth'

export const http = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

http.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  authStore.hydrate()
  if (authStore.accessToken) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${authStore.accessToken}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      const authStore = useAuthStore()
      authStore.clearSession()
      if (typeof window !== 'undefined') {
        const redirect = encodeURIComponent(window.location.pathname + window.location.search)
        if (!window.location.pathname.startsWith('/login')) {
          window.location.assign(`/login?redirect=${redirect}`)
        }
      }
    }
    return Promise.reject(error)
  },
)
