import { describe, expect, it } from 'vitest'

import { FRONTEND_DEFAULT_NEGATIVE_PROMPT, FRONTEND_DEFAULT_POSITIVE_PROMPT } from './generate-defaults'

describe('generate defaults', () => {
  it('uses the requested default positive prompt', () => {
    expect(FRONTEND_DEFAULT_POSITIVE_PROMPT).toBe(
      'wind turbines on grassland, modern wind power station, tall white turbine, clear sky, sunlight, realistic, clean composition, high detail, cinematic lighting',
    )
  })

  it('uses the requested default negative prompt', () => {
    expect(FRONTEND_DEFAULT_NEGATIVE_PROMPT).toBe(
      'cartoon, anime, sketch, low quality, blurry, deformed blades, broken structure, extra blades, people, text, watermark, logo',
    )
  })
})
