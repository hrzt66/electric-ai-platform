import { defineStore } from 'pinia'

type SessionPayload = {
  accessToken: string
  userName: string
  displayName: string
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: '',
    userName: '',
    displayName: '',
  }),
  actions: {
    setSession(payload: SessionPayload) {
      this.accessToken = payload.accessToken
      this.userName = payload.userName
      this.displayName = payload.displayName
    },
    clearSession() {
      this.accessToken = ''
      this.userName = ''
      this.displayName = ''
    },
  },
})
