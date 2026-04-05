import { describe, expect, it } from 'vitest'

import type { AuditEvent, GenerateTask } from '../../types/platform'
import { buildGenerationProgress } from './generation-progress'

function createTask(overrides: Partial<GenerateTask> = {}): GenerateTask {
  return {
    id: 7,
    job_type: 'generate',
    status: 'queued',
    stage: 'queued',
    error_message: '',
    model_name: 'sd15-electric',
    prompt: 'substation',
    negative_prompt: '',
    payload_json: '{}',
    created_at: '2026-04-06T09:00:00+08:00',
    updated_at: '2026-04-06T09:01:00+08:00',
    ...overrides,
  }
}

function createEvent(eventType: string, createdAt: string): AuditEvent {
  return {
    id: Math.floor(Math.random() * 10_000),
    job_id: 7,
    event_type: eventType,
    message: '',
    payload_json: '',
    created_at: createdAt,
  }
}

describe('buildGenerationProgress', () => {
  it('returns null when there is no current task', () => {
    expect(buildGenerationProgress(null, [])).toBeNull()
  })

  it('marks the generation phase as active when generation has started', () => {
    const progress = buildGenerationProgress(createTask({ status: 'generating', stage: 'generating' }), [
      createEvent('task.preparing', '2026-04-06T09:01:00+08:00'),
      createEvent('model.prepare', '2026-04-06T09:02:00+08:00'),
      createEvent('job_generating', '2026-04-06T09:03:00+08:00'),
    ])

    expect(progress?.percent).toBe(68)
    expect(progress?.headline).toBe('图像生成中')
    expect(progress?.phases.map((item) => item.state)).toEqual(['done', 'done', 'active', 'pending'])
  })

  it('marks every phase as done when the task is completed', () => {
    const progress = buildGenerationProgress(createTask({ status: 'completed', stage: 'completed' }), [
      createEvent('generation.completed', '2026-04-06T09:08:00+08:00'),
    ])

    expect(progress?.percent).toBe(100)
    expect(progress?.tone).toBe('success')
    expect(progress?.headline).toBe('生成完成')
    expect(progress?.phases.every((item) => item.state === 'done')).toBe(true)
  })

  it('keeps the current phase in failed state when the task aborts', () => {
    const progress = buildGenerationProgress(
      createTask({
        status: 'failed',
        stage: 'generating',
        error_message: 'CUDA out of memory',
      }),
      [createEvent('job_generating', '2026-04-06T09:03:00+08:00')],
    )

    expect(progress?.percent).toBe(68)
    expect(progress?.tone).toBe('danger')
    expect(progress?.headline).toBe('任务执行失败')
    expect(progress?.detail).toContain('CUDA out of memory')
    expect(progress?.phases.map((item) => item.state)).toEqual(['done', 'done', 'failed', 'pending'])
  })
})
