import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('app shell layout', () => {
  it('keeps the sidebar fixed to the viewport and scrolls content independently', () => {
    const content = readFileSync(resolve(__dirname, './AppShell.vue'), 'utf8')

    expect(content).toContain('height: 100vh;')
    expect(content).toContain('overflow: hidden;')
    expect(content).toContain('.sidebar {')
    expect(content).toContain('height: 100vh;')
    expect(content).toContain('.content {')
    expect(content).toContain('overflow-y: auto;')
    expect(content).toContain('.main {')
    expect(content).toContain('min-height: 0;')
  })

  it('contains the monitor navigation item in source', () => {
    const content = readFileSync(resolve(__dirname, './AppShell.vue'), 'utf8')

    expect(content).toContain("label: '运行监控'")
    expect(content).toContain("path: '/monitor'")
    expect(content).toContain("hint: 'Monitor'")
  })
})
