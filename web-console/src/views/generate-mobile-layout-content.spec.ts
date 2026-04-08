import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('generate mobile layout', () => {
  it('adds a parameter drawer and result-first mobile hooks', () => {
    const page = readFileSync(resolve(__dirname, './GenerateView.vue'), 'utf8')
    const panel = readFileSync(resolve(__dirname, '../components/workbench/ParameterPanel.vue'), 'utf8')

    expect(page).toContain('parameter-drawer')
    expect(page).toContain('open-parameter-button')
    expect(page).toContain('getWorkbenchSections')
    expect(page).toContain('mobile-section-strip')
    expect(panel).toContain('panel--drawer')
  })
})
