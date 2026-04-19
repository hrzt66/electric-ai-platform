import { describe, expect, it } from 'vitest'

import {
  GENERATION_RECOMMENDED_NEGATIVE_PROMPT,
  GENERATION_RECOMMENDED_POSITIVE_PROMPTS,
  pickRecommendedGenerationPrompt,
} from './generate-recommendations'

describe('generate recommendations', () => {
  it('picks the first recommended positive prompt for the lowest random bucket', () => {
    expect(pickRecommendedGenerationPrompt(0)).toBe(GENERATION_RECOMMENDED_POSITIVE_PROMPTS[0])
  })

  it('picks the last recommended positive prompt for the highest random bucket', () => {
    expect(pickRecommendedGenerationPrompt(0.999999)).toBe(
      GENERATION_RECOMMENDED_POSITIVE_PROMPTS[GENERATION_RECOMMENDED_POSITIVE_PROMPTS.length - 1],
    )
  })

  it('uses the requested fixed negative prompt copy', () => {
    expect(GENERATION_RECOMMENDED_NEGATIVE_PROMPT).toContain('CGI')
    expect(GENERATION_RECOMMENDED_NEGATIVE_PROMPT).toContain('duplicate structures')
    expect(GENERATION_RECOMMENDED_NEGATIVE_PROMPT).toContain('floating objects')
  })
})
