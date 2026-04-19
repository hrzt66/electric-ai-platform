import { describe, expect, it } from 'vitest'

import { SCORE_BANDS, getScoreBand, getScoreGradeLabel } from './score-grade'

describe('score bands', () => {
  it('keeps the five-level front-end score ranges stable', () => {
    expect(SCORE_BANDS.map((item) => item.label)).toEqual(['待改进', '偏低', '达标', '良好', '优秀'])
    expect(SCORE_BANDS.map((item) => item.min)).toEqual([0, 30, 50, 70, 85])
  })

  it('maps score boundaries to the expected front-end levels', () => {
    expect(getScoreBand(0).key).toBe('poor')
    expect(getScoreBand(29.99).key).toBe('poor')
    expect(getScoreBand(30).key).toBe('weak')
    expect(getScoreBand(49.99).key).toBe('weak')
    expect(getScoreBand(50).key).toBe('qualified')
    expect(getScoreBand(69.99).key).toBe('qualified')
    expect(getScoreBand(70).key).toBe('good')
    expect(getScoreBand(84.99).key).toBe('good')
    expect(getScoreBand(85).key).toBe('excellent')
    expect(getScoreBand(100).key).toBe('excellent')
  })

  it('returns a readable level label while leaving the score numeric', () => {
    expect(getScoreGradeLabel(27.3)).toBe('待改进')
    expect(getScoreGradeLabel(44.8)).toBe('偏低')
    expect(getScoreGradeLabel(63.1)).toBe('达标')
    expect(getScoreGradeLabel(74.2)).toBe('良好')
    expect(getScoreGradeLabel(92.5)).toBe('优秀')
  })
})
