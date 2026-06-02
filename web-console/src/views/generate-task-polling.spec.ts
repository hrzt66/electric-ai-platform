import { describe, expect, it } from 'vitest'

import { shouldResumeTaskPolling } from './generate-task-polling'

describe('shouldResumeTaskPolling', () => {
  it('returns false for terminal tasks so revisiting the page does not replay completion toasts', () => {
    expect(shouldResumeTaskPolling({ id: 139, status: 'completed' })).toBe(false)
    expect(shouldResumeTaskPolling({ id: 139, status: 'failed' })).toBe(false)
    expect(shouldResumeTaskPolling({ id: 139, status: 'scored' })).toBe(false)
    expect(shouldResumeTaskPolling({ id: 139, status: 'canceled' })).toBe(false)
  })

  it('returns true for active tasks that still need status refreshes', () => {
    expect(shouldResumeTaskPolling({ id: 139, status: 'queued' })).toBe(true)
    expect(shouldResumeTaskPolling({ id: 139, status: 'running' })).toBe(true)
    expect(shouldResumeTaskPolling({ id: 139, status: 'scoring' })).toBe(true)
  })

  it('returns false when there is no task context yet', () => {
    expect(shouldResumeTaskPolling(null)).toBe(false)
  })
})
