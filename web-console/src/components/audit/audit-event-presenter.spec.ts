import { describe, expect, it } from 'vitest'

import type { AuditEvent } from '../../types/platform'
import { presentAuditEvent } from './audit-event-presenter'

function createEvent(eventType: string, payloadJson = '', message = ''): AuditEvent {
  return {
    id: 1,
    job_id: 6,
    event_type: eventType,
    message,
    payload_json: payloadJson,
    created_at: '2026-04-06T15:30:00+08:00',
  }
}

describe('presentAuditEvent', () => {
  it('formats task.preparing into readable Chinese copy', () => {
    expect(presentAuditEvent(createEvent('task.preparing', '{"job_id":6,"model_name":"sd15-electric"}'))).toEqual({
      title: '任务已受理',
      description: '系统已接收任务，正在为模型 sd15-electric 准备运行环境。',
    })
  })

  it('formats generation.completed with image count', () => {
    expect(presentAuditEvent(createEvent('generation.completed', '{"job_id":6,"count":2}'))).toEqual({
      title: '图像生成完成',
      description: '本次生成已完成，共输出 2 张图像，正在进入评分与归档阶段。',
    })
  })

  it('prefers a readable failure message over raw payload JSON', () => {
    expect(
      presentAuditEvent(createEvent('task.failed', '{"job_id":6,"error_message":"CUDA out of memory"}', '')),
    ).toEqual({
      title: '任务失败',
      description: '任务执行失败：CUDA out of memory。',
    })
  })

  it('falls back to a Chinese field summary for unknown events', () => {
    expect(presentAuditEvent(createEvent('runtime.loaded', '{"job_id":6,"asset_count":3,"model_name":"sd15-electric"}'))).toEqual({
      title: '审计事件',
      description: '任务 ID 6，结果数量 3，模型 sd15-electric。',
    })
  })
})
