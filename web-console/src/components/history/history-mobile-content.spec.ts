import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('history mobile layout', () => {
  it('switches to cards and fullscreen detail on phones', () => {
    const table = readFileSync(resolve(__dirname, './HistoryTable.vue'), 'utf8')
    const filters = readFileSync(resolve(__dirname, './HistoryFilters.vue'), 'utf8')
    const drawer = readFileSync(resolve(__dirname, './HistoryDetailDrawer.vue'), 'utf8')

    expect(table).toContain('history-cards')
    expect(table).toContain('history-card--compact')
    expect(table).toContain('v-if="isMobile"')
    expect(filters).toContain('filters-toggle')
    expect(drawer).toContain('drawerSize')
  })
})
