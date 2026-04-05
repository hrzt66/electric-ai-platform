import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { describe, expect, it } from 'vitest'

import ResultPreview from './ResultPreview.vue'
import type { AssetHistoryItem, GenerateTask } from '../../types/platform'

function createAsset(overrides: Partial<AssetHistoryItem> = {}): AssetHistoryItem {
  return {
    id: 1,
    job_id: 6,
    image_name: 'tower-1.png',
    file_path: 'outputs/tower-1.png',
    model_name: 'sd15-electric',
    status: 'completed',
    positive_prompt: 'tower',
    negative_prompt: '',
    sampling_steps: 20,
    seed: 42,
    guidance_scale: 7.5,
    created_at: '2026-04-06T11:00:00+08:00',
    visual_fidelity: 88.2,
    text_consistency: 74.1,
    physical_plausibility: 81.4,
    composition_aesthetics: 79.5,
    total_score: 80.8,
    ...overrides,
  }
}

function createTask(overrides: Partial<GenerateTask> = {}): GenerateTask {
  return {
    id: 6,
    job_type: 'generate',
    status: 'completed',
    stage: 'completed',
    error_message: '',
    model_name: 'sd15-electric',
    prompt: 'tower',
    negative_prompt: '',
    payload_json: '{}',
    created_at: '2026-04-06T11:00:00+08:00',
    updated_at: '2026-04-06T11:02:00+08:00',
    ...overrides,
  }
}

async function renderPreview(props: {
  assets: AssetHistoryItem[]
  activeIndex: number
  task: GenerateTask | null
}) {
  const app = createSSRApp({
    render: () => h(ResultPreview, props),
  })

  app.component('el-image', {
    props: ['src', 'fit', 'previewSrcList', 'initialIndex'],
    setup(componentProps) {
      return () =>
        h('div', {
          class: 'el-image-stub',
          'data-src': componentProps.src,
          'data-fit': componentProps.fit,
          'data-preview-count': String(componentProps.previewSrcList?.length ?? 0),
          'data-initial-index': String(componentProps.initialIndex ?? -1),
        })
    },
  })

  app.component('el-tag', {
    props: ['type'],
    setup(_componentProps, { slots }) {
      return () => h('span', { class: 'el-tag-stub' }, slots.default?.())
    },
  })

  app.component('el-empty', {
    props: ['description'],
    setup(componentProps) {
      return () => h('div', { class: 'el-empty-stub' }, componentProps.description)
    },
  })

  return renderToString(app)
}

describe('ResultPreview', () => {
  it('renders the active image inside a fixed frame while preserving preview metadata', async () => {
    const html = await renderPreview({
      assets: [
        createAsset(),
        createAsset({
          id: 2,
          image_name: 'tower-2.png',
          file_path: 'outputs/tower-2.png',
        }),
      ],
      activeIndex: 1,
      task: createTask(),
    })

    expect(html).toContain('class="image-frame"')
    expect(html).toContain('data-fit="contain"')
    expect(html).toContain('data-preview-count="2"')
    expect(html).toContain('data-initial-index="1"')
    expect(html).toContain('任务 #6')
    expect(html).toContain('tower-2.png')
  })

  it('renders the waiting empty state when the task has no generated assets yet', async () => {
    const html = await renderPreview({
      assets: [],
      activeIndex: 0,
      task: createTask({
        status: 'generating',
        stage: 'generating',
      }),
    })

    expect(html).toContain('正在等待生成结果')
    expect(html).not.toContain('class="image-frame"')
  })
})
