import axios from 'axios'

import { useAuthStore } from '../stores/auth'

export const http = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

http.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  if (authStore.accessToken) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${authStore.accessToken}`
  }
  return config
})
