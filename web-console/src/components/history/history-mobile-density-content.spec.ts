import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('history mobile density', () => {
  it('renders compact mobile history rows and tighter detail sections', () => {
    const filters = readFileSync(resolve(__dirname, './HistoryFilters.vue'), 'utf8')
    const table = readFileSync(resolve(__dirname, './HistoryTable.vue'), 'utf8')
    const drawer = readFileSync(resolve(__dirname, './HistoryDetailDrawer.vue'), 'utf8')

    expect(filters).toContain('filters--compact')
    expect(table).toContain('history-card--compact')
    expect(drawer).toContain('drawer-body--compact')
  })
})
