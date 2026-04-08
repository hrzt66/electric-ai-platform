import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('app shell mobile chrome', () => {
  it('includes a drawer menu and bottom navigation for phones', () => {
    const content = readFileSync(resolve(__dirname, './AppShell.vue'), 'utf8')

    expect(content).toContain('menu-button')
    expect(content).toContain('mobile-nav')
    expect(content).toContain('el-drawer')
  })
})
