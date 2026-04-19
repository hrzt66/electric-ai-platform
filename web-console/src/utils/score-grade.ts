export type ScoreGrade = 'poor' | 'weak' | 'qualified' | 'good' | 'excellent'

export type ScoreBand = {
  key: ScoreGrade
  label: string
  min: number
  maxExclusive: number | null
}

export const SCORE_BANDS: ScoreBand[] = [
  { key: 'poor', label: '待改进', min: 0, maxExclusive: 30 },
  { key: 'weak', label: '偏低', min: 30, maxExclusive: 50 },
  { key: 'qualified', label: '达标', min: 50, maxExclusive: 70 },
  { key: 'good', label: '良好', min: 70, maxExclusive: 85 },
  { key: 'excellent', label: '优秀', min: 85, maxExclusive: null },
]

export function getScoreBand(score: number): ScoreBand {
  const value = Math.max(0, Math.min(score, 100))
  return SCORE_BANDS.find((item) => item.maxExclusive === null || value < item.maxExclusive) ?? SCORE_BANDS[SCORE_BANDS.length - 1]
}

export function getScoreGrade(score: number): ScoreGrade {
  return getScoreBand(score).key
}

export function getScoreGradeLabel(score: number): string {
  return getScoreBand(score).label
}
