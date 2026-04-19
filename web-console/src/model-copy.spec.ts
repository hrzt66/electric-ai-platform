import { describe, expect, it } from 'vitest'

import type { ModelRecord } from './types/platform'
import { localizeModelRecord } from './model-copy'

function buildModelRecord(overrides: Partial<ModelRecord>): ModelRecord {
  return {
    id: 1,
    model_name: 'ssd1b-electric',
    display_name: 'SSD-1B Electric',
    model_type: 'generation',
    service_name: 'model-service',
    status: 'available',
    description: 'SSD-1B SDXL distilled runtime tuned for lower-memory local generation',
    default_positive_prompt: '',
    default_negative_prompt: '',
    local_path: 'model/generation/ssd1b-electric',
    ...overrides,
  }
}

describe('model copy localization', () => {
  it('localizes known model display names and descriptions to Chinese', () => {
    const localized = localizeModelRecord(buildModelRecord({}))

    expect(localized.display_name).toBe('SSD-1B 电力极速版')
    expect(localized.description).toContain('低显存')
  })

  it('leaves unknown models unchanged', () => {
    const original = buildModelRecord({
      model_name: 'custom-model',
      display_name: 'Custom Model',
      description: 'Custom description',
    })

    expect(localizeModelRecord(original)).toEqual(original)
  })
})
