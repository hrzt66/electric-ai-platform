import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('mobile page layouts', () => {
  it('adds phone-specific layout hooks to the primary pages', () => {
    const login = readFileSync(resolve(__dirname, './LoginView.vue'), 'utf8')
    const dashboard = readFileSync(resolve(__dirname, './DashboardView.vue'), 'utf8')
    const models = readFileSync(resolve(__dirname, './ModelCenterView.vue'), 'utf8')
    const audit = readFileSync(resolve(__dirname, './TaskAuditView.vue'), 'utf8')

    expect(login).toContain('@media (max-width: 768px)')
    expect(dashboard).toContain('hero-actions')
    expect(models).toContain('@media (max-width: 768px)')
    expect(audit).toContain('@media (max-width: 768px)')
  })
})
