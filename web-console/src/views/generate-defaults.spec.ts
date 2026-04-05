import { describe, expect, it } from 'vitest'

import { FRONTEND_DEFAULT_NEGATIVE_PROMPT, FRONTEND_DEFAULT_POSITIVE_PROMPT } from './generate-defaults'

describe('generate defaults', () => {
  it('uses the requested default positive prompt', () => {
    expect(FRONTEND_DEFAULT_POSITIVE_PROMPT).toBe(
      'massive high voltage power tower at dramatic sunset, steel lattice pylon, thick power lines, corona discharge, insulators, golden hour, cinematic, photorealistic, ultra detailed, sharp focus',
    )
  })

  it('uses the requested default negative prompt', () => {
    expect(FRONTEND_DEFAULT_NEGATIVE_PROMPT).toBe(
      'blurry, lowres, deformed, bad anatomy, extra limbs, watermark, text, logo, cartoon, anime, low quality, jpeg artifacts, ugly, plastic, toy, mutated structure, asymmetrical, bad perspective',
    )
  })
})
