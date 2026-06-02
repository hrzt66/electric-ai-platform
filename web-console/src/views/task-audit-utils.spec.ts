import { describe, expect, it } from 'vitest'

import { resolveAuditTaskId } from './task-audit-utils'

describe('resolveAuditTaskId', () => {
  it('prefers the explicit route task id', () => {
    expect(resolveAuditTaskId({ routeTaskId: 99 })).toBe(99)
  })

  it('returns null for zero, negative, or missing route task ids', () => {
    expect(resolveAuditTaskId({ routeTaskId: 0 })).toBeNull()
    expect(resolveAuditTaskId({ routeTaskId: -3 })).toBeNull()
    expect(resolveAuditTaskId({ routeTaskId: undefined })).toBeNull()
  })
})
