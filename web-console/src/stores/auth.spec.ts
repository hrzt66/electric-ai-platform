import { createPinia, setActivePinia } from 'pinia'
import { describe, expect, it } from 'vitest'

import { useAuthStore } from './auth'

describe('auth store', () => {
  it('stores the access token after login success', async () => {
    setActivePinia(createPinia())
    const store = useAuthStore()

    store.setSession({
      accessToken: 'token-123',
      userName: 'admin',
      displayName: '系统管理员',
    })

    expect(store.accessToken).toBe('token-123')
    expect(store.displayName).toBe('系统管理员')
  })
})
