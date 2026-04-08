import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('generate mobile density', () => {
  it('uses compact mobile strips instead of tall stacked cards', () => {
    const page = readFileSync(resolve(__dirname, './GenerateView.vue'), 'utf8')
    const preview = readFileSync(resolve(__dirname, '../components/workbench/ResultPreview.vue'), 'utf8')
    const progress = readFileSync(resolve(__dirname, '../components/workbench/GenerationProgressCard.vue'), 'utf8')
    const radar = readFileSync(resolve(__dirname, '../components/workbench/ScoreRadar.vue'), 'utf8')

    expect(page).toContain('mobile-section-strip')
    expect(preview).toContain('preview-card--compact')
    expect(progress).toContain('progress-card--compact')
    expect(radar).toContain('score-card--compact')
  })
})
