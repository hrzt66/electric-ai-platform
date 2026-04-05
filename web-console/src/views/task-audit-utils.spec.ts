import { describe, expect, it } from 'vitest'

import type { AssetHistoryItem, GenerateTask } from '../types/platform'
import { resolveAuditTaskId } from './task-audit-utils'

describe('resolveAuditTaskId', () => {
  it('prefers the explicit route task id', () => {
    expect(
      resolveAuditTaskId({
        routeTaskId: 99,
        currentTaskId: 42,
        tasks: [
          {
            id: 7,
            job_type: 'generate',
            status: 'completed',
            stage: 'completed',
            error_message: '',
            model_name: 'sd15-electric',
            prompt: 'substation',
            negative_prompt: '',
            payload_json: '{}',
            created_at: '2026-04-06T08:00:00+08:00',
            updated_at: '2026-04-06T08:05:00+08:00',
          },
        ] satisfies GenerateTask[],
      }),
    ).toBe(99)
  })

  it('falls back to the current task id from memory', () => {
    expect(resolveAuditTaskId({ routeTaskId: null, currentTaskId: 42, tasks: [] })).toBe(42)
  })

  it('falls back to the latest known task when the page is opened directly', () => {
    expect(
      resolveAuditTaskId({
        routeTaskId: null,
        currentTaskId: null,
        tasks: [
          {
            id: 11,
            job_type: 'generate',
            status: 'completed',
            stage: 'completed',
            error_message: '',
            model_name: 'sd15-electric',
            prompt: 'substation',
            negative_prompt: '',
            payload_json: '{}',
            created_at: '2026-04-06T08:00:00+08:00',
            updated_at: '2026-04-06T08:01:00+08:00',
          },
          {
            id: 12,
            job_type: 'generate',
            status: 'generating',
            stage: 'generating',
            error_message: '',
            model_name: 'unipic2-kontext',
            prompt: 'tower',
            negative_prompt: '',
            payload_json: '{}',
            created_at: '2026-04-06T08:02:00+08:00',
            updated_at: '2026-04-06T08:04:00+08:00',
          },
        ] satisfies GenerateTask[],
      }),
    ).toBe(12)
  })

  it('falls back to the latest history record when the task list is unavailable', () => {
    expect(
      resolveAuditTaskId({
        routeTaskId: null,
        currentTaskId: null,
        tasks: [],
        history: [
          {
            id: 21,
            job_id: 3,
            image_name: '3_0_1.png',
            file_path: 'G:/electric-ai-runtime/outputs/images/3_0_1.png',
            model_name: 'sd15-electric',
            status: 'scored',
            positive_prompt: 'substation',
            negative_prompt: '',
            sampling_steps: 20,
            seed: 1,
            guidance_scale: 7.5,
            visual_fidelity: 88,
            text_consistency: 80,
            physical_plausibility: 82,
            composition_aesthetics: 79,
            total_score: 82.25,
            created_at: '2026-04-06T08:00:00+08:00',
          },
          {
            id: 22,
            job_id: 6,
            image_name: '6_0_1.png',
            file_path: 'G:/electric-ai-runtime/outputs/images/6_0_1.png',
            model_name: 'unipic2-kontext',
            status: 'scored',
            positive_prompt: 'tower',
            negative_prompt: '',
            sampling_steps: 28,
            seed: 2,
            guidance_scale: 6.5,
            visual_fidelity: 85,
            text_consistency: 77,
            physical_plausibility: 80,
            composition_aesthetics: 78,
            total_score: 80,
            created_at: '2026-04-06T08:05:00+08:00',
          },
        ] satisfies AssetHistoryItem[],
      }),
    ).toBe(6)
  })
})
