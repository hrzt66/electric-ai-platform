import { defineStore } from 'pinia'

type SessionPayload = {
  accessToken: string
  userName: string
  displayName: string
}

const AUTH_STORAGE_KEY = 'electric-ai-auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: '',
    userName: '',
    displayName: '',
    hydrated: false,
  }),
  getters: {
    isAuthenticated(state) {
      return Boolean(state.accessToken)
    },
  },
  actions: {
    hydrate() {
      // 避免应用初始化阶段重复从 localStorage 反序列化会话。
      if (this.hydrated) {
        return
      }

      this.hydrated = true
      const raw = getStorage()?.getItem(AUTH_STORAGE_KEY)
      if (!raw) {
        return
      }

      try {
        const payload = JSON.parse(raw) as Partial<SessionPayload>
        this.accessToken = payload.accessToken ?? ''
        this.userName = payload.userName ?? ''
        this.displayName = payload.displayName ?? ''
      } catch {
        // 本地会话被篡改或损坏时直接清掉，防止登录态进入半坏状态。
        getStorage()?.removeItem(AUTH_STORAGE_KEY)
      }
    },
    setSession(payload: SessionPayload) {
      this.accessToken = payload.accessToken
      this.userName = payload.userName
      this.displayName = payload.displayName
      this.hydrated = true
      getStorage()?.setItem(AUTH_STORAGE_KEY, JSON.stringify(payload))
    },
    clearSession() {
      this.accessToken = ''
      this.userName = ''
      this.displayName = ''
      this.hydrated = true
      getStorage()?.removeItem(AUTH_STORAGE_KEY)
    },
  },
})

function getStorage() {
  // SSR / 测试环境下不存在 localStorage，统一返回 null 让上层安全降级。
  if (typeof localStorage === 'undefined') {
    return null
  }
  return localStorage
}
