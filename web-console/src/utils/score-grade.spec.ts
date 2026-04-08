import { describe, expect, it } from 'vitest'

import { getScoreGrade } from './score-grade'

describe('getScoreGrade', () => {
  it('maps score boundaries to the expected grades', () => {
    expect(getScoreGrade(0)).toBe('E')
    expect(getScoreGrade(29.99)).toBe('E')
    expect(getScoreGrade(30)).toBe('D')
    expect(getScoreGrade(49.99)).toBe('D')
    expect(getScoreGrade(50)).toBe('C')
    expect(getScoreGrade(69.99)).toBe('C')
    expect(getScoreGrade(70)).toBe('B')
    expect(getScoreGrade(84.99)).toBe('B')
    expect(getScoreGrade(85)).toBe('A')
    expect(getScoreGrade(100)).toBe('A')
  })
})
