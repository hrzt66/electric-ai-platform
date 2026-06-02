import { describe, expect, it } from 'vitest'

import { localizeTaskAuditStatus } from './task-audit-status'

describe('localizeTaskAuditStatus', () => {
  it('maps task and asset statuses to Chinese labels', () => {
    expect(localizeTaskAuditStatus('queued')).toBe('排队中')
    expect(localizeTaskAuditStatus('running')).toBe('进行中')
    expect(localizeTaskAuditStatus('scored')).toBe('已完成')
    expect(localizeTaskAuditStatus('completed')).toBe('已完成')
    expect(localizeTaskAuditStatus('failed')).toBe('失败')
  })

  it('keeps unknown statuses unchanged and falls back for empty values', () => {
    expect(localizeTaskAuditStatus('archived')).toBe('archived')
    expect(localizeTaskAuditStatus('')).toBe('--')
    expect(localizeTaskAuditStatus()).toBe('--')
  })
})
