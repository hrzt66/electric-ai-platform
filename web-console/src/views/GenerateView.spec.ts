import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { describe, expect, it, vi } from 'vitest'

const platformStore = {
  models: [],
  currentTask: null,
  currentTaskId: null,
  currentAssets: [],
  currentTaskAudit: [],
  modelsLoadError: '',
  taskLoadError: '',
  submitting: false,
  fetchModels: vi.fn(),
  submitGenerateJob: vi.fn(),
  refreshTask: vi.fn(),
}

vi.mock('../stores/platform', () => ({
  usePlatformStore: () => platformStore,
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {} }),
}))

vi.mock('../components/workbench/ParameterPanel.vue', () => ({
  default: {
    name: 'ParameterPanel',
    props: ['form', 'scoringModels'],
    template:
      '<div class="parameter-panel-stub">{{ form.model_name }}|{{ form.scoring_model_name }}|{{ scoringModels?.[0]?.display_name }}|{{ scoringModels?.[0]?.description }}</div>',
  },
}))

vi.mock('../components/workbench/ResultPreview.vue', () => ({
  default: { template: '<div class="result-preview-stub">preview</div>' },
}))

vi.mock('../components/workbench/GenerationProgressCard.vue', () => ({
  default: { template: '<div class="progress-card-stub">progress</div>' },
}))

vi.mock('../components/workbench/ScoreRadar.vue', () => ({
  default: { template: '<div class="score-radar-stub">score</div>' },
}))

vi.mock('../components/audit/AuditTimeline.vue', () => ({
  default: { template: '<div class="audit-timeline-stub">audit</div>' },
}))

import GenerateView from './GenerateView.vue'

async function renderView() {
  const app = createSSRApp({
    render: () => h(GenerateView),
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

  return renderToString(app)
}

describe('GenerateView', () => {
  it('defaults to SSD-1B generation while keeping electric-score-v1 scoring', async () => {
    const html = await renderView()

    expect(html).toContain('ssd1b-electric|electric-score-v1')
  })

  it('shows localized fallback scoring model copy in the model intro area', async () => {
    const html = await renderView()

    expect(html).toContain('电力评分 V1（兼容版）')
    expect(html).toContain('兼容旧流程的四维评分模型')
  })
})
