# Score Grade Badges Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add visible `A/B/C/D/E` grade chips for the four score dimensions in the frontend while keeping total score display unchanged.

**Architecture:** Add one shared score-grade utility in `web-console/src/utils`, then consume it from the workbench score panel and the history detail drawer. Lock the mapping with boundary tests first, then add focused SSR component tests for the new chip rendering.

**Tech Stack:** Vue 3, TypeScript, Vitest, Vue SSR

---

### Task 1: Add score-grade mapping tests

**Files:**
- Create: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\utils\score-grade.spec.ts`
- Create: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\workbench\score-radar.spec.ts`
- Create: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\history\history-detail-drawer.spec.ts`

- [ ] **Step 1: Write the failing grade boundary test**

```ts
expect(getScoreGrade(0)).toBe('E')
expect(getScoreGrade(30)).toBe('D')
expect(getScoreGrade(50)).toBe('C')
expect(getScoreGrade(70)).toBe('B')
expect(getScoreGrade(85)).toBe('A')
```

- [ ] **Step 2: Write failing component rendering checks**

```ts
expect(html).toContain('grade-chip')
expect(html).toContain('>A<')
expect(html).toContain('>C<')
```

- [ ] **Step 3: Run the targeted tests and verify they fail**

Run: `cd web-console; npx vitest run src/utils/score-grade.spec.ts src/components/workbench/score-radar.spec.ts src/components/history/history-detail-drawer.spec.ts`

Expected: FAIL because the grade utility and grade chip rendering do not exist yet.

### Task 2: Implement shared score-grade utility

**Files:**
- Create: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\utils\score-grade.ts`

- [ ] **Step 1: Add the minimal grade mapping implementation**

```ts
export type ScoreGrade = 'A' | 'B' | 'C' | 'D' | 'E'

export function getScoreGrade(score: number): ScoreGrade {
  const value = Math.max(0, Math.min(score, 100))
  if (value < 30) return 'E'
  if (value < 50) return 'D'
  if (value < 70) return 'C'
  if (value < 85) return 'B'
  return 'A'
}
```

- [ ] **Step 2: Run the utility test and verify it passes**

Run: `cd web-console; npx vitest run src/utils/score-grade.spec.ts`

Expected: PASS

### Task 3: Add grade chips to the workbench score panel

**Files:**
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\workbench\ScoreRadar.vue`
- Test: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\workbench\score-radar.spec.ts`

- [ ] **Step 1: Extend metric view-models with grade values**
- [ ] **Step 2: Render one chip per dimension next to the numeric score**
- [ ] **Step 3: Add local chip styles keyed by grade**
- [ ] **Step 4: Run `npx vitest run src/components/workbench/score-radar.spec.ts` and verify PASS**

### Task 4: Add grade chips to the history detail drawer

**Files:**
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\history\HistoryDetailDrawer.vue`
- Test: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\history\history-detail-drawer.spec.ts`

- [ ] **Step 1: Build drawer score rows with optional grade metadata**
- [ ] **Step 2: Render chips for four dimensions only**
- [ ] **Step 3: Keep total score numeric-only**
- [ ] **Step 4: Run `npx vitest run src/components/history/history-detail-drawer.spec.ts` and verify PASS**

### Task 5: Run full frontend verification

**Files:**
- Verify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console`

- [ ] **Step 1: Run the full frontend test suite**

Run: `npm --prefix web-console run test`

Expected: PASS with all Vitest suites green.
