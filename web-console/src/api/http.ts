import axios from 'axios'

import { useAuthStore } from '../stores/auth'

// 所有前端平台请求都通过同一个 axios 实例走网关前缀。
export const http = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

http.interceptors.request.use((config) => {
  // 请求发出前自动补齐登录态，避免每个 API 单独处理 Bearer Token。
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
    // 如果网关返回 401，说明当前会话已失效，统一清理并跳回登录页。
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
