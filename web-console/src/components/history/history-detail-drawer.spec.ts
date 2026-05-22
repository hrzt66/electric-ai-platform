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
      file_path: 'model/image/27_0_1011411730.png',
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
    checked_image_path: 'model/image_check/27_0_1011411730.png',
    score_explanation: {
      checked_image_path: 'model/image_check/27_0_1011411730.png',
      dimensions: {
        visual_fidelity: {
          uses_yolo: true,
          summary: '画面细节尚可，但整体锐度仍有下降。',
          formula: '最终视觉保真 = 基础清晰度/曝光/对比度 + 检测主类结构清晰度补偿；按主类使用 5 套规则。',
          details: ['主判类别为 transmission_tower，视觉保真会按该电力主类切换对应规则。'],
          inputs: {
            raw_score: 49.4,
            calibrated_score: 49.4,
            final_score: 49.4,
            sharpness: 46.53,
            target_class: 'transmission_tower',
          },
        },
        text_consistency: {
          uses_yolo: true,
          summary: '提示词要求的关键设备没有完全检测到。',
          formula: '最终文本一致 = 检测匹配召回 + 目标置信度质量 + 少量语义先验补充。',
          details: ['仅检测到 tower，缺少 line 与 insulator。'],
          detections: [{ class_name: 'tower', confidence: 0.39 }],
          matched_classes: ['tower'],
          missing_classes: ['line', 'insulator'],
        },
      },
    },
  } as AssetDetail
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

  app.component('el-dialog', {
    props: ['modelValue', 'title'],
    setup(props, { slots }) {
      return () => h('section', { class: 'el-dialog-stub', 'data-open': String(Boolean(props.modelValue)) }, [slots.default?.()])
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
  it('renders five-level labels while still showing concrete numeric scores', async () => {
    const html = await renderDrawer(createDetail())

    expect(html).toContain('grade-chip')
    expect(html).toContain('>达标<')
    expect(html).toContain('>偏低<')
    expect(html).toContain('51.27')
    expect(html.match(/grade-chip/g)?.length).toBe(5)
  })

  it('renders clickable score-explanation triggers when explanation data is available', async () => {
    const html = await renderDrawer(createDetail())

    expect(html).toContain('查看视觉保真评分依据')
    expect(html).toContain('查看文本一致评分依据')
  })

  it('does not render the checked-image block in the asset detail body', async () => {
    const html = await renderDrawer(createDetail())

    expect(html).not.toContain('检测框结果图')
  })
})
