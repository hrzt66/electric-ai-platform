import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { describe, expect, it } from 'vitest'

import ScoreRadar from './ScoreRadar.vue'
import type { ScoreSummary } from '../../types/platform'

function createScores(overrides: Partial<ScoreSummary> = {}): ScoreSummary {
  return {
    visual_fidelity: 88.2,
    text_consistency: 62.05,
    physical_plausibility: 39.82,
    composition_aesthetics: 46.57,
    total_score: 51.27,
    ...overrides,
  }
}

async function renderRadar(scores: ScoreSummary | null) {
  const app = createSSRApp({
    render: () => h(ScoreRadar, { scores }),
  })

  return renderToString(app)
}

describe('ScoreRadar', () => {
  it('renders visible grade chips for the four score dimensions', async () => {
    const html = await renderRadar(createScores())

    expect(html).toContain('grade-chip')
    expect(html).toContain('>A<')
    expect(html).toContain('>C<')
    expect(html).toContain('>D<')
  })
})
