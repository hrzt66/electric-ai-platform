import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '../stores/auth'

describe('app router', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: () => null,
      setItem: () => undefined,
      removeItem: () => undefined,
      clear: () => undefined,
    })
    setActivePinia(createPinia())
  })

  it('redirects unauthenticated users to login', async () => {
    const { createAppRouter } = await import('./index')
    const router = createAppRouter(createMemoryHistory())

    await router.push('/generate')

    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query.redirect).toBe('/generate')
  })

  it('redirects authenticated users away from login', async () => {
    const { createAppRouter } = await import('./index')
    const router = createAppRouter(createMemoryHistory())
    const authStore = useAuthStore()
    authStore.setSession({
      accessToken: 'token-123',
      userName: 'admin',
      displayName: '系统管理员',
    })

    await router.push('/login')

    expect(router.currentRoute.value.path).toBe('/dashboard')
  })

  it('allows authenticated users to access monitor route', async () => {
    const { createAppRouter } = await import('./index')
    const router = createAppRouter(createMemoryHistory())
    const authStore = useAuthStore()
    authStore.setSession({
      accessToken: 'token-123',
      userName: 'admin',
      displayName: '系统管理员',
    })

    await router.push('/monitor')

    expect(router.currentRoute.value.path).toBe('/monitor')
    expect(router.currentRoute.value.matched.length).toBeGreaterThan(0)
    expect(router.currentRoute.value.matched.at(-1)?.path).toBe('/monitor')
  })
})
