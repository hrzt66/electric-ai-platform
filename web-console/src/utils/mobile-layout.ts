export const TABLET_BREAKPOINT = 1100
export const MOBILE_BREAKPOINT = 768
export const SMALL_MOBILE_BREAKPOINT = 480

export function getWorkbenchSections(width: number): string[] {
  return width <= MOBILE_BREAKPOINT
    ? ['preview', 'progress', 'scores', 'controls', 'audit']
    : ['controls', 'preview', 'side']
}

export function shouldUseHistoryCards(width: number): boolean {
  return width <= MOBILE_BREAKPOINT
}
