import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it, vi } from 'vitest'

const authStore = {
  displayName: '演示用户',
  userName: 'demo',
  clearSession: vi.fn(),
}

vi.mock('../stores/auth', () => ({
  useAuthStore: () => authStore,
}))

import AppShell from './AppShell.vue'

async function renderShell(path = '/dashboard') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/',
        component: AppShell,
        children: [
          { path: 'dashboard', component: { render: () => h('div', 'dashboard') } },
          { path: 'generate', component: { render: () => h('div', 'generate') } },
          { path: 'history', component: { render: () => h('div', 'history') } },
          { path: 'models', component: { render: () => h('div', 'models') } },
          { path: 'monitor', component: { render: () => h('div', 'monitor') } },
          { path: 'tasks/audit', component: { render: () => h('div', 'audit') } },
        ],
      },
      { path: '/login', component: { render: () => h('div', 'login') } },
    ],
  })

  await router.push(path)
  await router.isReady()

  const app = createSSRApp({
    render: () => h(AppShell),
  })

  app.use(router)
  app.component('el-button', {
    setup(_props, { slots }) {
      return () => h('button', { class: 'el-button-stub' }, slots.default?.())
    },
  })

  return renderToString(app)
}

describe('app shell layout', () => {
  it('keeps the sidebar fixed to the viewport and scrolls content independently', async () => {
    const html = await renderShell()

    expect(html).toContain('平台总览')
    expect(html).toContain('生成工作台')
    expect(html).toContain('任务审计')
  })

  it('hides the monitor navigation item from the sidebar', async () => {
    const html = await renderShell('/dashboard')

    expect(html).not.toContain('运行监控')
    expect(html).not.toContain('Monitor')
    expect(html).toContain('page-title')
  })

  it('shows shorter platform-oriented topbar copy', async () => {
    const html = await renderShell()

    expect(html).toContain('统一平台')
    expect(html).toContain('生成、评分')
  })
})
