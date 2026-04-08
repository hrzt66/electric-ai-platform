import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('mobile page layouts', () => {
  it('adds phone-specific compact hooks to the primary pages', () => {
    const login = readFileSync(resolve(__dirname, './LoginView.vue'), 'utf8')
    const dashboard = readFileSync(resolve(__dirname, './DashboardView.vue'), 'utf8')
    const models = readFileSync(resolve(__dirname, './ModelCenterView.vue'), 'utf8')
    const audit = readFileSync(resolve(__dirname, './TaskAuditView.vue'), 'utf8')

    expect(login).toContain('mobile-login-summary')
    expect(dashboard).toContain('mobile-compact-card')
    expect(models).toContain('mobile-compact-card')
    expect(audit).toContain('mobile-compact-card')
  })
})
