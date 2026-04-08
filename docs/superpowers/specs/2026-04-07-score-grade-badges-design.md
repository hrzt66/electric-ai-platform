# Score Grade Badges Design

**Date:** 2026-04-07

## Goal

Show letter grades for the four scoring dimensions in the frontend using visible badge/chip styling.

## Decision

Use compact inline grade chips for the four dimension scores only.

- Dimension score ranges map to grades:
  - `0-30`: `E`
  - `30-50`: `D`
  - `50-70`: `C`
  - `70-85`: `B`
  - `85-100`: `A`
- Total score keeps the old numeric-only display.
- The grade mapping is implemented once in a shared frontend utility.
- The badge/chip UI is shown in:
  - the workbench score panel
  - the history detail drawer

## Files

- Create: `web-console/src/utils/score-grade.ts`
- Create: `web-console/src/utils/score-grade.spec.ts`
- Create: `web-console/src/components/workbench/score-radar.spec.ts`
- Create: `web-console/src/components/history/history-detail-drawer.spec.ts`
- Modify: `web-console/src/components/workbench/ScoreRadar.vue`
- Modify: `web-console/src/components/history/HistoryDetailDrawer.vue`

## Behavior

- Every dimension shows:
  - the numeric score
  - a nearby visual chip with the letter grade
- Grade chips use distinct tones so the user can visually distinguish strong and weak results quickly.
- Total score remains unchanged and does not show a letter grade.

## Risks

- Boundary handling can be inconsistent if duplicated across components.
  - Mitigation: centralize the mapping in one utility and test boundary cases.
- The UI may become visually noisy if total score also gets a badge.
  - Mitigation: keep total score numeric-only.

## Verification

- `npx vitest run src/utils/score-grade.spec.ts`
- `npx vitest run src/components/workbench/score-radar.spec.ts src/components/history/history-detail-drawer.spec.ts`
- `npm --prefix web-console run test`
