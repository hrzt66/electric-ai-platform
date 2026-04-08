# Web Console Mobile Responsive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every `web-console` page usable on phones without removing any features by adding mobile navigation, drawer-based secondary panels, and single-column responsive layouts.

**Architecture:** Keep the current Vue routes and Pinia stores intact, and localize the responsive behavior to `AppShell.vue`, page-level layout components, and a few pure TypeScript viewport helpers. Because this repo currently uses Vitest without component-mount helpers, the plan combines pure logic tests, source-content tests for responsive template branches, and `vite build` verification for scoped CSS changes.

**Tech Stack:** Vue 3, TypeScript, Element Plus, Pinia, Vue Router, Vite, Vitest, scoped CSS

---

## File Structure

### Create

- `web-console/src/utils/mobile-layout.ts`
  Shared viewport constants and small pure helpers for mobile/tablet decisions.
- `web-console/src/utils/mobile-layout.spec.ts`
  Unit tests for breakpoint and layout ordering helpers.
- `web-console/src/components/app-shell-content.spec.ts`
  Source-content test that guards the mobile drawer and bottom navigation hooks.
- `web-console/src/views/mobile-page-layout-content.spec.ts`
  Source-content test for login, dashboard, model center, and audit mobile layout branches.
- `web-console/src/views/generate-mobile-layout-content.spec.ts`
  Source-content test for generate page mobile drawer/result-first structure.
- `web-console/src/components/history/history-mobile-content.spec.ts`
  Source-content test for history card layout and full-screen drawer behavior.

### Modify

- `web-console/src/App.vue`
  Add global safe-area and mobile spacing rules so the bottom navigation does not cover content.
- `web-console/src/components/AppShell.vue`
  Convert the shell into a desktop sidebar + mobile top bar/bottom nav/drawer pattern.
- `web-console/src/views/LoginView.vue`
  Stack the stage and login card for phones.
- `web-console/src/views/DashboardView.vue`
  Reflow hero, summary cards, and panels into mobile-friendly vertical blocks.
- `web-console/src/views/GenerateView.vue`
  Reorder the workbench for result-first mobile presentation and host the parameter drawer trigger.
- `web-console/src/components/workbench/ParameterPanel.vue`
  Support drawer/mobile styling and single-column controls.
- `web-console/src/components/workbench/ResultPreview.vue`
  Tighten image and metadata layout for smaller screens.
- `web-console/src/components/workbench/GenerationProgressCard.vue`
  Improve stacked mobile rendering for status and phases.
- `web-console/src/components/workbench/ScoreRadar.vue`
  Allow the radar header and metric list to collapse cleanly on phones.
- `web-console/src/views/HistoryView.vue`
  Host collapsible filters and the dual desktop/mobile history presentation.
- `web-console/src/components/history/HistoryFilters.vue`
  Add mobile-friendly single-column and collapsible filter layout.
- `web-console/src/components/history/HistoryTable.vue`
  Keep `el-table` for desktop and render card items for phones.
- `web-console/src/components/history/HistoryDetailDrawer.vue`
  Use a near-fullscreen drawer and stacked score sections on phones.
- `web-console/src/views/ModelCenterView.vue`
  Stack hero and model cards cleanly on phones.
- `web-console/src/views/TaskAuditView.vue`
  Collapse the two-column audit layout into a single mobile flow.

## Task 1: Add shared viewport helpers

**Files:**
- Create: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\utils\mobile-layout.ts`
- Create: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\utils\mobile-layout.spec.ts`

- [ ] **Step 1: Write the failing test**

```ts
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/utils/mobile-layout.spec.ts`

Expected: FAIL with an error like `Cannot find module './mobile-layout'`.

- [ ] **Step 3: Write minimal implementation**

```ts
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/utils/mobile-layout.spec.ts`

Expected: PASS with `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add web-console/src/utils/mobile-layout.ts web-console/src/utils/mobile-layout.spec.ts
git commit -m "test: add mobile layout helpers"
```

## Task 2: Refactor the application shell for mobile chrome

**Files:**
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\App.vue`
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\AppShell.vue`
- Create: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\app-shell-content.spec.ts`
- Test: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\utils\mobile-layout.spec.ts`

- [ ] **Step 1: Write the failing shell content test**

```ts
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('app shell mobile chrome', () => {
  it('includes a drawer menu and bottom navigation for phones', () => {
    const content = readFileSync(resolve(__dirname, './AppShell.vue'), 'utf8')

    expect(content).toContain('menu-button')
    expect(content).toContain('mobile-nav')
    expect(content).toContain('el-drawer')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/app-shell-content.spec.ts`

Expected: FAIL because `AppShell.vue` does not yet contain `mobile-nav`, `menu-button`, or `el-drawer`.

- [ ] **Step 3: Implement the shell changes**

Update `AppShell.vue` to track viewport width and drive the mobile shell:

```ts
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { MOBILE_BREAKPOINT } from '../utils/mobile-layout'

const viewportWidth = ref(typeof window === 'undefined' ? 1280 : window.innerWidth)
const mobileMenuOpen = ref(false)
const isMobile = computed(() => viewportWidth.value <= MOBILE_BREAKPOINT)

function syncViewport() {
  viewportWidth.value = window.innerWidth
  if (!isMobile.value) {
    mobileMenuOpen.value = false
  }
}

onMounted(() => window.addEventListener('resize', syncViewport))
onBeforeUnmount(() => window.removeEventListener('resize', syncViewport))
```

Add the mobile top bar, drawer, and bottom nav in `AppShell.vue`:

```vue
<button v-if="isMobile" class="menu-button" type="button" @click="mobileMenuOpen = true">
  <span />
  <span />
  <span />
</button>

<el-drawer v-model="mobileMenuOpen" direction="ltr" size="min(86vw, 320px)" class="mobile-shell-drawer">
  <nav class="drawer-nav">
    <button
      v-for="item in navItems"
      :key="item.path"
      class="nav-item"
      :class="{ active: item.path === activePath }"
      type="button"
      @click="go(item.path); mobileMenuOpen = false"
    >
      <span class="nav-label">{{ item.label }}</span>
      <span class="nav-path">{{ item.hint }}</span>
    </button>
  </nav>
</el-drawer>

<nav v-if="isMobile" class="mobile-nav">
  <button
    v-for="item in navItems"
    :key="item.path"
    class="mobile-nav-item"
    :class="{ active: item.path === activePath }"
    type="button"
    @click="go(item.path)"
  >
    <span>{{ item.label }}</span>
  </button>
</nav>
```

Add global safe-area spacing in `App.vue`:

```css
body {
  overflow-x: hidden;
}

@media (max-width: 768px) {
  body {
    padding-bottom: calc(80px + env(safe-area-inset-bottom, 0px));
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/components/app-shell-content.spec.ts src/utils/mobile-layout.spec.ts`

Expected: PASS with both specs green.

- [ ] **Step 5: Commit**

```bash
git add web-console/src/App.vue web-console/src/components/AppShell.vue web-console/src/components/app-shell-content.spec.ts
git commit -m "feat: add mobile app shell chrome"
```

## Task 3: Reflow the login, overview, model, and audit pages

**Files:**
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\views\LoginView.vue`
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\views\DashboardView.vue`
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\views\ModelCenterView.vue`
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\views\TaskAuditView.vue`
- Create: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\views\mobile-page-layout-content.spec.ts`

- [ ] **Step 1: Write the failing page-layout content test**

```ts
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/views/mobile-page-layout-content.spec.ts`

Expected: FAIL because those files do not yet contain the new hooks.

- [ ] **Step 3: Implement the page layout updates**

Add a dedicated action row and mobile stacking rules in `DashboardView.vue`:

```vue
<section class="hero">
  <div>
    ...
  </div>
  <div class="hero-actions">
    <router-link class="hero-link" to="/generate">进入生成工作台</router-link>
  </div>
</section>
```

```css
@media (max-width: 768px) {
  .hero {
    align-items: stretch;
  }

  .hero-actions,
  .hero-link {
    width: 100%;
  }

  .summary-grid,
  .list-grid {
    grid-template-columns: 1fr;
  }
}
```

Tighten the login page stack in `LoginView.vue`:

```css
@media (max-width: 768px) {
  .control-stage {
    padding: 24px 16px 8px;
  }

  .stage-copy,
  .status-grid,
  .login-shell {
    gap: 14px;
  }

  .status-grid {
    grid-template-columns: 1fr;
  }
}
```

Use the same single-column rule in `ModelCenterView.vue` and `TaskAuditView.vue`:

```css
@media (max-width: 768px) {
  .hero,
  .summary-card,
  .content-grid,
  .model-grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/views/mobile-page-layout-content.spec.ts src/views/login-content.spec.ts`

Expected: PASS, and the existing login copy test stays green.

- [ ] **Step 5: Commit**

```bash
git add web-console/src/views/LoginView.vue web-console/src/views/DashboardView.vue web-console/src/views/ModelCenterView.vue web-console/src/views/TaskAuditView.vue web-console/src/views/mobile-page-layout-content.spec.ts
git commit -m "feat: stack overview pages for mobile"
```

## Task 4: Convert the generate workbench to a result-first mobile flow

**Files:**
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\views\GenerateView.vue`
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\workbench\ParameterPanel.vue`
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\workbench\ResultPreview.vue`
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\workbench\GenerationProgressCard.vue`
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\workbench\ScoreRadar.vue`
- Create: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\views\generate-mobile-layout-content.spec.ts`

- [ ] **Step 1: Write the failing generate layout content test**

```ts
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('generate mobile layout', () => {
  it('adds a parameter drawer and result-first mobile hooks', () => {
    const page = readFileSync(resolve(__dirname, './GenerateView.vue'), 'utf8')
    const panel = readFileSync(resolve(__dirname, '../components/workbench/ParameterPanel.vue'), 'utf8')

    expect(page).toContain('parameter-drawer')
    expect(page).toContain('open-parameter-button')
    expect(page).toContain('getWorkbenchSections')
    expect(panel).toContain('panel--drawer')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/views/generate-mobile-layout-content.spec.ts`

Expected: FAIL because the generate page is still a three-column desktop layout.

- [ ] **Step 3: Implement the mobile workbench flow**

In `GenerateView.vue`, use the helper from Task 1 and host the drawer state:

```ts
import { MOBILE_BREAKPOINT, getWorkbenchSections } from '../utils/mobile-layout'

const viewportWidth = ref(typeof window === 'undefined' ? 1280 : window.innerWidth)
const parameterDrawerOpen = ref(false)
const isMobile = computed(() => viewportWidth.value <= MOBILE_BREAKPOINT)
const workbenchSections = computed(() => getWorkbenchSections(viewportWidth.value))
```

Add the trigger and drawer:

```vue
<el-button
  v-if="isMobile"
  class="open-parameter-button"
  type="primary"
  plain
  @click="parameterDrawerOpen = true"
>
  打开参数面板
</el-button>

<el-drawer
  v-if="isMobile"
  v-model="parameterDrawerOpen"
  class="parameter-drawer"
  direction="btt"
  size="88%"
>
  <ParameterPanel
    class="panel--drawer"
    :form="form"
    :models="generationModels"
    :scoring-models="scoringModels"
    :submitting="platformStore.submitting"
    @submit="submit"
    @fill-defaults="fillDefaults"
  />
</el-drawer>
```

Update the mobile layout in `GenerateView.vue`:

```css
@media (max-width: 768px) {
  .workbench {
    grid-template-columns: 1fr;
  }

  .preview-column,
  .side-column {
    order: initial;
  }

  .status-card {
    max-height: none;
  }
}
```

Make `ParameterPanel.vue` phone-friendly:

```css
.panel--drawer {
  height: auto;
  min-height: 100%;
  border-radius: 24px 24px 0 0;
  box-shadow: none;
}

@media (max-width: 768px) {
  .form,
  .grid-two {
    grid-template-columns: 1fr;
  }
}
```

Tighten card headers in `ResultPreview.vue`, `GenerationProgressCard.vue`, and `ScoreRadar.vue`:

```css
@media (max-width: 768px) {
  .preview-header,
  .progress-header,
  .score-header {
    flex-direction: column;
    align-items: stretch;
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/views/generate-mobile-layout-content.spec.ts src/components/workbench/generation-progress.spec.ts src/components/workbench/result-preview.spec.ts src/components/workbench/score-radar.spec.ts`

Expected: PASS with the new content spec and the existing pure workbench specs still green.

- [ ] **Step 5: Commit**

```bash
git add web-console/src/views/GenerateView.vue web-console/src/components/workbench/ParameterPanel.vue web-console/src/components/workbench/ResultPreview.vue web-console/src/components/workbench/GenerationProgressCard.vue web-console/src/components/workbench/ScoreRadar.vue web-console/src/views/generate-mobile-layout-content.spec.ts
git commit -m "feat: reflow generate workbench for mobile"
```

## Task 5: Replace mobile history tables with cards and fullscreen detail

**Files:**
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\views\HistoryView.vue`
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\history\HistoryFilters.vue`
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\history\HistoryTable.vue`
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\history\HistoryDetailDrawer.vue`
- Create: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\src\components\history\history-mobile-content.spec.ts`

- [ ] **Step 1: Write the failing history mobile content test**

```ts
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('history mobile layout', () => {
  it('switches to cards and fullscreen detail on phones', () => {
    const table = readFileSync(resolve(__dirname, './HistoryTable.vue'), 'utf8')
    const filters = readFileSync(resolve(__dirname, './HistoryFilters.vue'), 'utf8')
    const drawer = readFileSync(resolve(__dirname, './HistoryDetailDrawer.vue'), 'utf8')

    expect(table).toContain('history-cards')
    expect(table).toContain('v-if="isMobile"')
    expect(filters).toContain('filters-toggle')
    expect(drawer).toContain('drawerSize')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/components/history/history-mobile-content.spec.ts`

Expected: FAIL because the history view still only renders a desktop table and fixed-width drawer.

- [ ] **Step 3: Implement the history mobile presentation**

In `HistoryView.vue`, add a local toggle for filters:

```ts
const filtersExpanded = ref(false)
```

Update `HistoryFilters.vue` with a phone toggle and single-column layout:

```vue
<button class="filters-toggle" type="button" @click="emit('toggle')">
  {{ expanded ? '收起筛选' : '展开筛选' }}
</button>
<div class="grid" :class="{ collapsed: !expanded }">
  ...
</div>
```

Render cards in `HistoryTable.vue` when `isMobile` is true:

```vue
<div v-if="isMobile" class="history-cards">
  <article v-for="row in items" :key="row.id" class="history-card" @click="emit('open', row)">
    <img class="thumb" :src="buildImageUrl(row.file_path)" :alt="row.image_name" />
    <div class="history-card__body">
      <strong>{{ row.image_name }}</strong>
      <p>{{ row.positive_prompt }}</p>
      <div class="history-card__meta">
        <span>{{ row.model_name }}</span>
        <span>总分 {{ row.total_score.toFixed(2) }}</span>
        <span>{{ row.created_at }}</span>
      </div>
    </div>
  </article>
</div>
```

Make `HistoryDetailDrawer.vue` responsive:

```ts
const drawerSize = computed(() => (window.innerWidth <= 768 ? '100%' : '720px'))
```

```vue
<el-drawer :model-value="visible" :size="drawerSize" @update:model-value="emit('update:visible', $event)">
```

```css
@media (max-width: 768px) {
  .score-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .drawer-image {
    min-height: 220px;
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/components/history/history-mobile-content.spec.ts src/components/history/history-detail-drawer.spec.ts`

Expected: PASS with the new mobile content spec and the existing drawer behavior spec still green.

- [ ] **Step 5: Commit**

```bash
git add web-console/src/views/HistoryView.vue web-console/src/components/history/HistoryFilters.vue web-console/src/components/history/HistoryTable.vue web-console/src/components/history/HistoryDetailDrawer.vue web-console/src/components/history/history-mobile-content.spec.ts
git commit -m "feat: add mobile history cards and drawer layout"
```

## Task 6: Run full verification and capture the final state

**Files:**
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\docs\superpowers\plans\2026-04-08-web-console-mobile-responsive.md`
  Mark completed tasks as checked during execution.
- Test: `E:\毕业设计\golang-毕业设计\.worktrees\electric-score-v2\web-console\package.json`

- [ ] **Step 1: Run the focused Vitest suite**

Run: `npx vitest run src/utils/mobile-layout.spec.ts src/components/app-shell-content.spec.ts src/views/mobile-page-layout-content.spec.ts src/views/generate-mobile-layout-content.spec.ts src/components/history/history-mobile-content.spec.ts src/router/index.spec.ts src/views/login-content.spec.ts src/components/workbench/generation-progress.spec.ts src/components/workbench/result-preview.spec.ts src/components/workbench/score-radar.spec.ts src/components/history/history-detail-drawer.spec.ts`

Expected: PASS for the mobile layout additions and the existing route/workbench/history specs.

- [ ] **Step 2: Run the production build**

Run: `npm run build`

Expected: PASS with Vite emitting the `dist/` bundle and no TypeScript template errors.

- [ ] **Step 3: Review the diff for only the intended files**

Run: `git status --short`

Expected: only the planned `web-console` source files and this plan file are modified, plus the known unrelated `python-ai-service/.idea/` entry remains untouched.

- [ ] **Step 4: Commit the completed responsive implementation**

```bash
git add web-console/src/App.vue web-console/src/components/AppShell.vue web-console/src/components/app-shell-content.spec.ts web-console/src/components/history/HistoryDetailDrawer.vue web-console/src/components/history/HistoryFilters.vue web-console/src/components/history/HistoryTable.vue web-console/src/components/history/history-mobile-content.spec.ts web-console/src/components/workbench/GenerationProgressCard.vue web-console/src/components/workbench/ParameterPanel.vue web-console/src/components/workbench/ResultPreview.vue web-console/src/components/workbench/ScoreRadar.vue web-console/src/utils/mobile-layout.spec.ts web-console/src/utils/mobile-layout.ts web-console/src/views/DashboardView.vue web-console/src/views/GenerateView.vue web-console/src/views/HistoryView.vue web-console/src/views/LoginView.vue web-console/src/views/ModelCenterView.vue web-console/src/views/TaskAuditView.vue web-console/src/views/generate-mobile-layout-content.spec.ts web-console/src/views/mobile-page-layout-content.spec.ts
git commit -m "feat: make web console mobile responsive"
```

## Self-Review

### Spec coverage

- Mobile top bar, bottom navigation, and drawer shell are covered by Task 2.
- Login, dashboard, model center, and audit page stacking are covered by Task 3.
- Result-first generate page, parameter drawer, and responsive workbench cards are covered by Task 4.
- History cards, collapsible filters, and responsive detail drawer are covered by Task 5.
- Global verification and regression coverage are covered by Task 6.

No spec gaps remain.

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” markers remain.
- Every task includes file paths, code snippets, commands, and expected outcomes.

### Type consistency

- The shared breakpoint constants (`TABLET_BREAKPOINT`, `MOBILE_BREAKPOINT`, `SMALL_MOBILE_BREAKPOINT`) are introduced once in Task 1 and reused consistently.
- The mobile history/card shell names (`history-cards`, `filters-toggle`, `drawer-size`) match the content specs and implementation steps.
- The mobile history/card shell names (`history-cards`, `filters-toggle`, `drawerSize`) match the content specs and implementation steps.
- The generate mobile hooks (`parameter-drawer`, `open-parameter-button`, `panel--drawer`) are named consistently across the task.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-08-web-console-mobile-responsive.md`.

Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Because you asked me to make the follow-up decisions and this session does not have explicit permission to spawn subagents, the implementation should proceed with **Inline Execution**.
