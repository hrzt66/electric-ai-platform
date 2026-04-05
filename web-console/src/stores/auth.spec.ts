import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from './auth'

describe('auth store', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', createStorageMock())
    setActivePinia(createPinia())
  })

  it('stores the access token after login success', async () => {
    const store = useAuthStore()

    store.setSession({
      accessToken: 'token-123',
      userName: 'admin',
      displayName: '系统管理员',
    })

    expect(store.accessToken).toBe('token-123')
    expect(store.displayName).toBe('系统管理员')
  })

  it('hydrates session from localStorage', async () => {
    localStorage.setItem(
      'electric-ai-auth',
      JSON.stringify({
        accessToken: 'token-from-cache',
        userName: 'cached-admin',
        displayName: '缓存管理员',
      }),
    )

    const store = useAuthStore()
    store.hydrate()

    expect(store.accessToken).toBe('token-from-cache')
    expect(store.userName).toBe('cached-admin')
    expect(store.displayName).toBe('缓存管理员')
  })

  it('removes the persisted session on logout', async () => {
    const store = useAuthStore()
    store.setSession({
      accessToken: 'token-123',
      userName: 'admin',
      displayName: '系统管理员',
    })

    store.clearSession()

    expect(store.accessToken).toBe('')
    expect(localStorage.getItem('electric-ai-auth')).toBeNull()
  })
})

function createStorageMock() {
  const state = new Map<string, string>()

  return {
    getItem(key: string) {
      return state.has(key) ? state.get(key)! : null
    },
    setItem(key: string, value: string) {
      state.set(key, value)
    },
    removeItem(key: string) {
      state.delete(key)
    },
    clear() {
      state.clear()
    },
  }
}
