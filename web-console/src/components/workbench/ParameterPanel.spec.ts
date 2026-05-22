import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { describe, expect, it } from 'vitest'

import ParameterPanel from './ParameterPanel.vue'

const generationModels = [
  {
    id: 1,
    model_name: 'ssd1b-electric',
    display_name: 'SSD-1B Electric',
    model_type: 'generation',
    service_name: 'model-service',
    status: 'available',
    description: 'Local generation model',
    default_positive_prompt: '',
    default_negative_prompt: '',
    local_path: 'model/generation/ssd1b-electric',
  },
  {
    id: 2,
    model_name: 'gpt-image-2',
    display_name: 'GPT Image 2',
    model_type: 'generation',
    service_name: 'model-service',
    status: 'available',
    description: 'API image model',
    default_positive_prompt: '',
    default_negative_prompt: '',
    local_path: 'api/openai/gpt-image-2',
  },
]

const scoringModels = [
  {
    id: 3,
    model_name: 'electric-score-v1',
    display_name: 'Electric Score V1',
    model_type: 'scoring',
    service_name: 'model-service',
    status: 'available',
    description: 'Scoring model',
    default_positive_prompt: '',
    default_negative_prompt: '',
    local_path: 'model/scoring/electric-score-v1',
  },
]

async function renderPanel(modelName: string) {
  const app = createSSRApp({
    render: () =>
      h(ParameterPanel, {
        form: {
          prompt: 'prompt',
          negative_prompt: 'negative',
          model_name: modelName,
          scoring_model_name: 'electric-score-v1',
          seed: -1,
          steps: 20,
          guidance_scale: 7.5,
          width: 512,
          height: 512,
          num_images: 1,
        },
        models: generationModels,
        scoringModels,
        submitting: false,
      }),
  })

  app.component('el-form', { setup: (_props, { slots }) => () => h('form', slots.default?.()) })
  app.component('el-form-item', { props: ['label'], setup: (props, { slots }) => () => h('div', `${props.label}:${slots.default?.()?.length ?? 0}`) })
  app.component('el-select', { setup: (_props, { slots }) => () => h('div', slots.default?.()) })
  app.component('el-option', { props: ['label'], setup: (props) => () => h('span', props.label) })
  app.component('el-input', { setup: () => () => h('input') })
  app.component('el-input-number', { setup: () => () => h('input') })
  app.component('el-slider', { setup: () => () => h('input') })
  app.component('el-button', { setup: (_props, { slots }) => () => h('button', slots.default?.()) })
  app.component('el-tag', { setup: (_props, { slots }) => () => h('span', slots.default?.()) })

  return renderToString(app)
}

describe('ParameterPanel', () => {
  it('shows advanced controls for local generation models', async () => {
    const html = await renderPanel('ssd1b-electric')

    expect(html).toContain('负向提示词')
    expect(html).toContain('随机种子')
    expect(html).toContain('采样步数')
    expect(html).toContain('引导强度')
    expect(html).toContain('输出数量')
    expect(html).toContain('宽度')
    expect(html).toContain('高度')
  })

  it('hides advanced controls for gpt-image-2', async () => {
    const html = await renderPanel('gpt-image-2')

    expect(html).not.toContain('负向提示词')
    expect(html).not.toContain('随机种子')
    expect(html).not.toContain('采样步数')
    expect(html).not.toContain('引导强度')
    expect(html).not.toContain('输出数量')
    expect(html).not.toContain('宽度')
    expect(html).not.toContain('高度')
    expect(html).toContain('正向提示词')
    expect(html).toContain('评分模型')
  })

  it('shows the apply system prompt entry copy', async () => {
    const html = await renderPanel('ssd1b-electric')

    expect(html).toContain('应用系统提示词')
  })
})
