import { describe, expect, it } from 'vitest'

import {
  detectPromptTargetClass,
  getSystemPromptPreset,
  pickRandomSystemPromptPreset,
} from './generate-recommendations'

describe('generate recommendations', () => {
  it('detects wind turbine prompts from english and chinese hints', () => {
    expect(detectPromptTargetClass('utility scale wind turbine on grassland')).toBe('wind_turbine')
    expect(detectPromptTargetClass('风机草原巡检')).toBe('wind_turbine')
  })

  it('picks the first random preset for the lowest random bucket', () => {
    const preset = pickRandomSystemPromptPreset(0)
    expect(preset.targetClass).toBe('substation_primary')
    expect(preset.positivePrompt).toBe('electrical substation')
  })

  it('picks the last random preset for the highest random bucket', () => {
    const preset = pickRandomSystemPromptPreset(0.999999)
    expect(preset.targetClass).toBe('dam')
    expect(preset.positivePrompt).toBe('dam')
  })

  it('keeps all five system presets available', () => {
    expect(getSystemPromptPreset('substation_primary').positivePrompt).toBe('electrical substation')
    expect(getSystemPromptPreset('transmission_tower').positivePrompt).toBe('transmission tower')
    expect(getSystemPromptPreset('wind_turbine').positivePrompt).toBe('wind turbine')
    expect(getSystemPromptPreset('solar_panel').positivePrompt).toBe('solar panel')
    expect(getSystemPromptPreset('dam').negativePrompt).toContain('floating equipment')
  })
})
