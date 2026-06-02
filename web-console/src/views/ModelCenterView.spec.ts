import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { describe, expect, it, vi } from 'vitest'

const push = vi.fn()
const platformStore = {
  models: [] as any[],
  modelsLoadError: '',
  fetchModels: vi.fn(),
}

vi.mock('../stores/platform', () => ({
  usePlatformStore: () => platformStore,
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
}))

import ModelCenterView from './ModelCenterView.vue'

async function renderView() {
  const app = createSSRApp({
    render: () => h(ModelCenterView),
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

  app.component('el-button', {
    setup(_props, { slots }) {
      return () => h('button', { class: 'el-button-stub' }, slots.default?.())
    },
  })

  return renderToString(app)
}

describe('ModelCenterView', () => {
  it('only shows the curated generation models in the generation section', async () => {
    platformStore.models = [
      {
        id: 1,
        model_name: 'sd15-electric',
        display_name: 'SD 1.5 电力基础版',
        model_type: 'generation',
        service_name: 'python-ai-service',
        status: 'available',
        description: '',
        default_positive_prompt: '',
        default_negative_prompt: '',
        local_path: 'model/generation/sd15-electric',
      },
      {
        id: 2,
        model_name: 'sd15-electric-specialized',
        display_name: 'SD 1.5 电力专精版',
        model_type: 'generation',
        service_name: 'python-ai-service',
        status: 'available',
        description: '',
        default_positive_prompt: '',
        default_negative_prompt: '',
        local_path: 'model/generation/sd15-electric-specialized',
      },
      {
        id: 3,
        model_name: 'ssd1b-electric',
        display_name: 'SSD-1B 电力极速版',
        model_type: 'generation',
        service_name: 'python-ai-service',
        status: 'available',
        description: '',
        default_positive_prompt: '',
        default_negative_prompt: '',
        local_path: 'model/generation/ssd1b-electric',
      },
      {
        id: 4,
        model_name: 'gpt-image-2',
        display_name: 'GPT Image 2 电力云生图',
        model_type: 'generation',
        service_name: 'python-ai-service',
        status: 'available',
        description: '',
        default_positive_prompt: '',
        default_negative_prompt: '',
        local_path: 'api/openai/gpt-image-2',
      },
      {
        id: 5,
        model_name: 'unipic2-kontext',
        display_name: 'UniPic2 电力场景版',
        model_type: 'generation',
        service_name: 'python-ai-service',
        status: 'available',
        description: '',
        default_positive_prompt: '',
        default_negative_prompt: '',
        local_path: 'model/generation/unipic2-kontext',
      },
      {
        id: 6,
        model_name: 'electric-score-v1',
        display_name: '电力评分 V1（兼容版）',
        model_type: 'scoring',
        service_name: 'python-ai-service',
        status: 'available',
        description: '',
        default_positive_prompt: '',
        default_negative_prompt: '',
        local_path: 'model/scoring/electric-score-v1',
      },
    ]

    const html = await renderView()

    expect(html).toContain('生成模型')
    expect(html).toContain('4 个')
    expect(html).toContain('SD 1.5 电力基础版')
    expect(html).toContain('SD 1.5 电力专精版')
    expect(html).toContain('SSD-1B 电力极速版')
    expect(html).toContain('GPT Image 2 电力云生图')
    expect(html).not.toContain('UniPic2 电力场景版')
    expect(html).toContain('评分模型')
    expect(html).toContain('电力评分 V1（兼容版）')
  })
})
