import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../audit/AuditTimeline.vue', () => ({
  default: {
    name: 'AuditTimeline',
    template: '<div class="audit-timeline-stub">audit</div>',
  },
}))

import HistoryDetailDrawer from './HistoryDetailDrawer.vue'
import type { AssetDetail, AuditEvent } from '../../types/platform'

function createDetail(): AssetDetail {
  return {
    asset: {
      id: 25,
      job_id: 27,
      image_name: '27_0_1011411730.png',
      file_path: 'G:/electric-ai-runtime/outputs/images/27_0_1011411730.png',
      model_name: 'sd15-electric',
      status: 'scored',
      created_at: '2026-04-07T02:27:33+08:00',
      updated_at: '2026-04-07T02:27:33+08:00',
    },
    prompt: {
      positive_prompt: 'wind turbines on grassland',
      negative_prompt: 'blurry',
      sampling_steps: 20,
      seed: 1011411730,
      guidance_scale: 7.5,
    },
    score: {
      visual_fidelity: 49.4,
      text_consistency: 62.05,
      physical_plausibility: 39.82,
      composition_aesthetics: 46.57,
      total_score: 51.27,
    },
  }
}

async function renderDrawer(detail: AssetDetail | null, auditEvents: AuditEvent[] = []) {
  const app = createSSRApp({
    render: () =>
      h(HistoryDetailDrawer, {
        visible: true,
        detail,
        auditEvents,
      }),
  })

  app.component('el-drawer', {
    props: ['modelValue', 'size'],
    setup(_props, { slots }) {
      return () => h('section', { class: 'el-drawer-stub' }, [slots.header?.(), slots.default?.()])
    },
  })

  app.component('el-tag', {
    setup(_props, { slots }) {
      return () => h('span', { class: 'el-tag-stub' }, slots.default?.())
    },
  })

  app.component('el-image', {
    props: ['src'],
    setup(props) {
      return () => h('img', { class: 'el-image-stub', src: props.src })
    },
  })

  app.component('el-descriptions', {
    setup(_props, { slots }) {
      return () => h('dl', { class: 'el-descriptions-stub' }, slots.default?.())
    },
  })

  app.component('el-descriptions-item', {
    props: ['label'],
    setup(props, { slots }) {
      return () => h('div', { class: 'el-descriptions-item-stub', 'data-label': props.label }, slots.default?.())
    },
  })
  return renderToString(app)
}

describe('HistoryDetailDrawer', () => {
  it('renders four dimension grade chips while keeping total score numeric only', async () => {
    const html = await renderDrawer(createDetail())

    expect(html).toContain('grade-chip')
    expect(html).toContain('>C<')
    expect(html).toContain('>D<')
    expect(html.match(/grade-chip/g)?.length).toBe(4)
  })
})
