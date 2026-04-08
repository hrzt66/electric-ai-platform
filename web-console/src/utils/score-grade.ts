export type ScoreGrade = 'A' | 'B' | 'C' | 'D' | 'E'

export function getScoreGrade(score: number): ScoreGrade {
  const value = Math.max(0, Math.min(score, 100))

  if (value < 30) {
    return 'E'
  }
  if (value < 50) {
    return 'D'
  }
  if (value < 70) {
    return 'C'
  }
  if (value < 85) {
    return 'B'
  }

  return 'A'
}
