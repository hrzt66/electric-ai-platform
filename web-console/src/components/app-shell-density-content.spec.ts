import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('app shell mobile density', () => {
  it('thins the mobile top bar and bottom nav content', () => {
    const content = readFileSync(resolve(__dirname, './AppShell.vue'), 'utf8')

    expect(content).toContain('topbar-status-dot')
    expect(content).toContain('mobile-nav-text')
    expect(content).toContain('@media (max-width: 768px)')
  })
})
