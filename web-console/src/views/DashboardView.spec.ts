import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { beforeEach, describe, expect, it, vi } from 'vitest'

type MonitorStoreMock = {
  tasks: unknown[]
  history: unknown[]
  models: unknown[]
  historyTotal: number
  taskAuditTotal: number
  monitorOverview: Record<string, unknown> | null
  tasksLoadError: string
  historyLoadError: string
  modelsLoadError: string
  fetchTasks: ReturnType<typeof vi.fn>
  fetchHistory: ReturnType<typeof vi.fn>
  fetchHistoryPage: ReturnType<typeof vi.fn>
  fetchTaskAuditPage: ReturnType<typeof vi.fn>
  fetchModels: ReturnType<typeof vi.fn>
  fetchMonitorOverview: ReturnType<typeof vi.fn>
}

const platformStore: MonitorStoreMock = {
  tasks: [],
  history: [],
  models: [],
  historyTotal: 0,
  taskAuditTotal: 0,
  monitorOverview: null,
  tasksLoadError: '',
  historyLoadError: '',
  modelsLoadError: '',
  fetchTasks: vi.fn(),
  fetchHistory: vi.fn(),
  fetchHistoryPage: vi.fn(),
  fetchTaskAuditPage: vi.fn(),
  fetchModels: vi.fn(),
  fetchMonitorOverview: vi.fn(),
}

const authStore = {
  displayName: '演示用户',
  userName: 'demo',
}

vi.mock('../stores/platform', () => ({
  usePlatformStore: () => platformStore,
}))

vi.mock('../stores/auth', () => ({
  useAuthStore: () => authStore,
}))

import DashboardView from './DashboardView.vue'

async function renderView() {
  const app = createSSRApp({
    render: () => h(DashboardView),
  })

  app.component('el-alert', {
    props: ['title'],
    setup(props) {
      return () => h('div', { class: 'el-alert-stub' }, props.title)
    },
  })

  app.component('el-skeleton', {
    setup() {
      return () => h('div', { class: 'el-skeleton-stub' }, 'skeleton')
    },
  })

  app.component('el-tag', {
    setup(_props, { slots }) {
      return () => h('span', { class: 'el-tag-stub' }, slots.default?.())
    },
  })

  app.component('el-empty', {
    props: ['description'],
    setup(props) {
      return () => h('div', { class: 'el-empty-stub' }, props.description)
    },
  })

  app.component('router-link', {
    props: ['to'],
    setup(props, { slots }) {
      return () => h('a', { class: 'router-link-stub', href: String(props.to ?? '') }, slots.default?.())
    },
  })

  return renderToString(app)
}

describe('DashboardView', () => {
  beforeEach(() => {
    platformStore.tasks = []
    platformStore.history = []
    platformStore.models = []
    platformStore.historyTotal = 0
    platformStore.taskAuditTotal = 0
    platformStore.tasksLoadError = ''
    platformStore.historyLoadError = ''
    platformStore.modelsLoadError = ''
    platformStore.fetchTasks.mockReset()
    platformStore.fetchHistory.mockReset()
    platformStore.fetchHistoryPage.mockReset()
    platformStore.fetchTaskAuditPage.mockReset()
    platformStore.fetchModels.mockReset()
    platformStore.fetchMonitorOverview.mockReset()
  })

  it('renders summary cards and task/model sections without monitor panel', async () => {
    platformStore.monitorOverview = { overall_health: 'warning' }

    const html = await renderView()

    expect(html).toContain('统一平台总览')
    expect(html).toContain('生成、评分')
    expect(html).toContain('任务总数')
    expect(html).toContain('历史资产')
    expect(html).toContain('可用模型')
    expect(html).toContain('href=&quot;/generate&quot;')
    expect(html).toContain('进入生成工作台')
    expect(html).not.toContain('AI 运行健康')
    expect(html).not.toContain('进入监控驾驶舱')
  })

  it('renders recent task and model panels', async () => {
    platformStore.tasks = [
      {
        id: 12,
        model_name: 'electric-gen',
        prompt: '变电站巡检图像',
        status: 'running',
        updated_at: '2026-05-03T10:00:00Z',
      },
    ]
    platformStore.taskAuditTotal = 12
    platformStore.historyTotal = 30
    platformStore.models = [
      {
        id: 7,
        model_name: 'score-v1',
        display_name: '评分模型',
        description: '用于缺陷评分',
        local_path: '/model/score-v1',
        status: 'available',
      },
    ]
    platformStore.monitorOverview = { overall_health: 'healthy' }

    const html = await renderView()

    expect(html).toContain('最近任务')
    expect(html).toContain('#12 electric-gen')
    expect(html).toContain('变电站巡检图像')
    expect(html).toContain('可用模型')
    expect(html).toContain('评分模型')
    expect(html).toContain('用于缺陷评分')
  })
})
