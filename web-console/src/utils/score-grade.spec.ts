import { describe, expect, it } from 'vitest'

import { SCORE_BANDS, getScoreBand, getScoreGradeLabel } from './score-grade'

describe('score bands', () => {
  it('keeps the five-level front-end score ranges stable', () => {
    expect(SCORE_BANDS.map((item) => item.label)).toEqual(['较差', '偏低', '达标', '良好', '优秀'])
    expect(SCORE_BANDS.map((item) => item.min)).toEqual([0, 50, 70, 85, 95])
  })

  it('maps score boundaries to the expected front-end levels', () => {
    expect(getScoreBand(0).key).toBe('poor')
    expect(getScoreBand(49.99).key).toBe('poor')
    expect(getScoreBand(50).key).toBe('weak')
    expect(getScoreBand(69.99).key).toBe('weak')
    expect(getScoreBand(70).key).toBe('qualified')
    expect(getScoreBand(84.99).key).toBe('qualified')
    expect(getScoreBand(85).key).toBe('good')
    expect(getScoreBand(94.99).key).toBe('good')
    expect(getScoreBand(95).key).toBe('excellent')
    expect(getScoreBand(100).key).toBe('excellent')
  })

  it('returns a readable level label while leaving the score numeric', () => {
    expect(getScoreGradeLabel(27.3)).toBe('较差')
    expect(getScoreGradeLabel(44.8)).toBe('较差')
    expect(getScoreGradeLabel(63.1)).toBe('偏低')
    expect(getScoreGradeLabel(74.2)).toBe('达标')
    expect(getScoreGradeLabel(92.5)).toBe('良好')
    expect(getScoreGradeLabel(97.5)).toBe('优秀')
  })
})
