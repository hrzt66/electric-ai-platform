import { describe, expect, it } from 'vitest'

import {
  MOBILE_BREAKPOINT,
  SMALL_MOBILE_BREAKPOINT,
  TABLET_BREAKPOINT,
  getWorkbenchSections,
  shouldUseHistoryCards,
} from './mobile-layout'

describe('mobile layout helpers', () => {
  it('keeps breakpoint constants stable', () => {
    expect(TABLET_BREAKPOINT).toBe(1100)
    expect(MOBILE_BREAKPOINT).toBe(768)
    expect(SMALL_MOBILE_BREAKPOINT).toBe(480)
  })

  it('switches workbench order on phones', () => {
    expect(getWorkbenchSections(1366)).toEqual(['controls', 'preview', 'side'])
    expect(getWorkbenchSections(768)).toEqual(['preview', 'progress', 'scores', 'controls', 'audit'])
  })

  it('uses history cards only for mobile widths', () => {
    expect(shouldUseHistoryCards(1024)).toBe(false)
    expect(shouldUseHistoryCards(768)).toBe(true)
  })
})
