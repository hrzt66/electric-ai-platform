# Web Console Mobile Density Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the mobile version of `web-console` feel thin and compact by shrinking the shell chrome, flattening tall cards into short modules, and keeping the desktop layout unchanged.

**Architecture:** Keep the existing Vue routes, Pinia stores, and mobile functional behaviors from the previous responsive pass. This refinement only changes mobile density and visual hierarchy inside `AppShell.vue`, the generate/history flows, and the remaining top-level pages through scoped CSS and light template trimming. Testing stays source-content-heavy plus targeted Vitest suites and a production build because the repo already uses source assertions for responsive branches.

**Tech Stack:** Vue 3, TypeScript, Element Plus, Vue Router, Pinia, Vite, Vitest, scoped CSS

---

## File Structure

### Create

- `.worktrees/electric-score-v2/web-console/src/components/app-shell-density-content.spec.ts`
  Guards that mobile shell chrome was thinned instead of just kept functionally responsive.
- `.worktrees/electric-score-v2/web-console/src/views/generate-mobile-density-content.spec.ts`
  Guards that the mobile generate page uses short module hooks instead of stacked tall cards.
- `.worktrees/electric-score-v2/web-console/src/components/history/history-mobile-density-content.spec.ts`
  Guards that history cards, filters, and detail drawer use compact mobile hooks.

### Modify

- `.worktrees/electric-score-v2/web-console/src/App.vue`
  Tighten mobile safe-area spacing and add shared compact mobile tokens.
- `.worktrees/electric-score-v2/web-console/src/components/AppShell.vue`
  Thin the mobile top bar and bottom navigation.
- `.worktrees/electric-score-v2/web-console/src/components/app-shell-content.spec.ts`
  Keep the existing mobile shell structure test green.
- `.worktrees/electric-score-v2/web-console/src/views/GenerateView.vue`
  Convert mobile stacked sections into short strips and compact audit/status blocks.
- `.worktrees/electric-score-v2/web-console/src/components/workbench/ParameterPanel.vue`
  Reduce form density and weaken model-tip blocks on phones.
- `.worktrees/electric-score-v2/web-console/src/components/workbench/ResultPreview.vue`
  Shorten preview header/meta/thumbnail vertical space.
- `.worktrees/electric-score-v2/web-console/src/components/workbench/GenerationProgressCard.vue`
  Turn the progress panel into a thinner status block on phones.
- `.worktrees/electric-score-v2/web-console/src/components/workbench/ScoreRadar.vue`
  Prioritize total score and short metric rows over a tall chart block.
- `.worktrees/electric-score-v2/web-console/src/views/HistoryView.vue`
  Keep filters collapsed by default on phones and reduce page spacing.
- `.worktrees/electric-score-v2/web-console/src/components/history/HistoryFilters.vue`
  Make the filter shell thinner and mobile-first compact.
- `.worktrees/electric-score-v2/web-console/src/components/history/HistoryTable.vue`
  Compress mobile cards into short horizontal rows.
- `.worktrees/electric-score-v2/web-console/src/components/history/HistoryDetailDrawer.vue`
  Thin score chips, descriptions, and drawer spacing on phones.
- `.worktrees/electric-score-v2/web-console/src/views/LoginView.vue`
  Keep only the key login content above the fold on phones.
- `.worktrees/electric-score-v2/web-console/src/views/DashboardView.vue`
  Apply compact mobile card spacing and reduce summary height.
- `.worktrees/electric-score-v2/web-console/src/views/ModelCenterView.vue`
  Apply compact mobile card spacing and reduce summary height.
- `.worktrees/electric-score-v2/web-console/src/views/TaskAuditView.vue`
  Apply compact mobile card spacing and reduce summary height.
- `.worktrees/electric-score-v2/web-console/src/views/mobile-page-layout-content.spec.ts`
  Keep the existing broad mobile-page coverage green after compacting those pages.

## Task 1: Add regression tests for thin mobile density

**Files:**
- Create: `.worktrees/electric-score-v2/web-console/src/components/app-shell-density-content.spec.ts`
- Create: `.worktrees/electric-score-v2/web-console/src/views/generate-mobile-density-content.spec.ts`
- Create: `.worktrees/electric-score-v2/web-console/src/components/history/history-mobile-density-content.spec.ts`

- [ ] **Step 1: Write the failing tests**

```ts
// src/components/app-shell-density-content.spec.ts
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('app shell mobile density', () => {
  it('thins the mobile top bar and bottom nav content', () => {
    const content = readFileSync(resolve(__dirname, './AppShell.vue'), 'utf8')

    expect(content).toContain('topbar-status-dot')
    expect(content).toContain('mobile-nav-text')
    expect(content).toContain('@media (max-width: 768px)')
  })
})
```

```ts
// src/views/generate-mobile-density-content.spec.ts
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('generate mobile density', () => {
  it('uses compact mobile strips instead of tall stacked cards', () => {
    const page = readFileSync(resolve(__dirname, './GenerateView.vue'), 'utf8')
    const preview = readFileSync(resolve(__dirname, '../components/workbench/ResultPreview.vue'), 'utf8')
    const progress = readFileSync(resolve(__dirname, '../components/workbench/GenerationProgressCard.vue'), 'utf8')
    const radar = readFileSync(resolve(__dirname, '../components/workbench/ScoreRadar.vue'), 'utf8')

    expect(page).toContain('mobile-section-strip')
    expect(preview).toContain('preview-card--compact')
    expect(progress).toContain('progress-card--compact')
    expect(radar).toContain('score-card--compact')
  })
})
```

```ts
// src/components/history/history-mobile-density-content.spec.ts
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

describe('history mobile density', () => {
  it('renders compact mobile history rows and tighter detail sections', () => {
    const filters = readFileSync(resolve(__dirname, './HistoryFilters.vue'), 'utf8')
    const table = readFileSync(resolve(__dirname, './HistoryTable.vue'), 'utf8')
    const drawer = readFileSync(resolve(__dirname, './HistoryDetailDrawer.vue'), 'utf8')

    expect(filters).toContain('filters--compact')
    expect(table).toContain('history-card--compact')
    expect(drawer).toContain('drawer-body--compact')
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
npx vitest run src/components/app-shell-density-content.spec.ts src/views/generate-mobile-density-content.spec.ts src/components/history/history-mobile-density-content.spec.ts
```

Expected: FAIL because none of the new compact hooks exist yet.

- [ ] **Step 3: Commit the failing tests**

```bash
git add web-console/src/components/app-shell-density-content.spec.ts web-console/src/views/generate-mobile-density-content.spec.ts web-console/src/components/history/history-mobile-density-content.spec.ts
git commit -m "test: add mobile density regression coverage"
```

## Task 2: Thin the global mobile shell and safe-area spacing

**Files:**
- Modify: `.worktrees/electric-score-v2/web-console/src/App.vue`
- Modify: `.worktrees/electric-score-v2/web-console/src/components/AppShell.vue`
- Modify: `.worktrees/electric-score-v2/web-console/src/components/app-shell-content.spec.ts`
- Test: `.worktrees/electric-score-v2/web-console/src/components/app-shell-density-content.spec.ts`

- [ ] **Step 1: Update the shell tests first**

Extend the existing shell content test so it still checks the responsive structure while the new density test checks the compact hooks:

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
    expect(content).toContain('topbar-status-dot')
  })
})
```

- [ ] **Step 2: Run the focused shell tests and confirm only the old one passes**

Run:

```bash
npx vitest run src/components/app-shell-content.spec.ts src/components/app-shell-density-content.spec.ts
```

Expected: `app-shell-content.spec.ts` PASS, `app-shell-density-content.spec.ts` FAIL.

- [ ] **Step 3: Implement the thinner mobile tokens in `App.vue`**

Add shared compact mobile variables and reduce the bottom safe-area padding:

```vue
<style>
:root {
  color-scheme: light;
  --ea-bg: #edf2f7;
  --ea-surface: #ffffff;
  --ea-surface-alt: #f8fafc;
  --ea-text: #17202b;
  --ea-text-muted: #53606f;
  --ea-primary: #1447a6;
  --ea-primary-strong: #0f3278;
  --ea-accent: #d3a449;
  --ea-border: rgba(15, 23, 32, 0.08);
  --ea-shadow: 0 18px 36px rgba(15, 23, 32, 0.08);
  --ea-mobile-card-radius: 14px;
  --ea-mobile-card-padding: 12px;
  --ea-mobile-card-shadow: 0 8px 18px rgba(15, 23, 32, 0.08);
}

@media (max-width: 768px) {
  body {
    padding-bottom: calc(64px + env(safe-area-inset-bottom, 0px));
  }
}
</style>
```

- [ ] **Step 4: Implement the thinner mobile shell in `AppShell.vue`**

Replace the long mobile badge with a short status dot row and make each bottom-nav item a thinner text block:

```vue
<header class="topbar" :class="{ 'topbar-mobile': isMobile }">
  <div class="topbar-main">
    <button v-if="isMobile" class="menu-button" type="button" aria-label="打开导航菜单" @click="mobileMenuOpen = true">
      <span />
      <span />
      <span />
    </button>

    <div>
      <p class="eyebrow" v-if="!isMobile">本机原生运行时</p>
      <h1 class="page-title">{{ currentTitle }}</h1>
    </div>
  </div>

  <div v-if="isMobile" class="topbar-status">
    <span class="topbar-status-dot" />
    <span class="topbar-status-text">在线</span>
  </div>

  <div v-else class="topbar-badge">
    <span class="badge-dot" />
    Go 微服务边界 / Python 模型中心 / 实时审计
  </div>
</header>

<nav v-if="isMobile" class="mobile-nav">
  <button
    v-for="item in navItems"
    :key="item.path"
    class="mobile-nav-item"
    :class="{ active: item.path === activePath }"
    type="button"
    :disabled="item.path === activePath || navigating"
    @click="go(item.path)"
  >
    <span class="mobile-nav-text">
      <span class="mobile-nav-label">{{ item.label }}</span>
      <span class="mobile-nav-hint">{{ item.hint }}</span>
    </span>
  </button>
</nav>
```

Apply the compact mobile CSS:

```css
.topbar-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  color: #f8fafc;
  font-size: 0.76rem;
}

.topbar-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #0f9d58;
}

.mobile-nav-text {
  display: grid;
  gap: 1px;
  justify-items: center;
}

@media (max-width: 768px) {
  .topbar-mobile {
    padding: 10px 14px 8px;
    gap: 8px;
  }

  .page-title {
    font-size: 1.18rem;
    line-height: 1.1;
  }

  .menu-button {
    width: 38px;
    height: 38px;
    border-radius: 12px;
  }

  .mobile-nav {
    gap: 4px;
    padding: 6px 8px calc(6px + env(safe-area-inset-bottom, 0px));
  }

  .mobile-nav-item {
    min-height: 40px;
    padding: 6px 2px;
    border-radius: 12px;
  }

  .mobile-nav-label {
    font-size: 0.72rem;
  }

  .mobile-nav-hint {
    display: none;
  }
}
```

- [ ] **Step 5: Run the shell tests**

Run:

```bash
npx vitest run src/components/app-shell-content.spec.ts src/components/app-shell-density-content.spec.ts
```

Expected: PASS with both specs green.

- [ ] **Step 6: Commit the shell density change**

```bash
git add web-console/src/App.vue web-console/src/components/AppShell.vue web-console/src/components/app-shell-content.spec.ts web-console/src/components/app-shell-density-content.spec.ts
git commit -m "feat: thin mobile shell chrome"
```

## Task 3: Flatten the generate workbench into short mobile strips

**Files:**
- Modify: `.worktrees/electric-score-v2/web-console/src/views/GenerateView.vue`
- Modify: `.worktrees/electric-score-v2/web-console/src/components/workbench/ParameterPanel.vue`
- Modify: `.worktrees/electric-score-v2/web-console/src/components/workbench/ResultPreview.vue`
- Modify: `.worktrees/electric-score-v2/web-console/src/components/workbench/GenerationProgressCard.vue`
- Modify: `.worktrees/electric-score-v2/web-console/src/components/workbench/ScoreRadar.vue`
- Test: `.worktrees/electric-score-v2/web-console/src/views/generate-mobile-layout-content.spec.ts`
- Test: `.worktrees/electric-score-v2/web-console/src/views/generate-mobile-density-content.spec.ts`
- Test: `.worktrees/electric-score-v2/web-console/src/components/workbench/generation-progress.spec.ts`
- Test: `.worktrees/electric-score-v2/web-console/src/components/workbench/result-preview.spec.ts`
- Test: `.worktrees/electric-score-v2/web-console/src/components/workbench/score-radar.spec.ts`

- [ ] **Step 1: Keep the existing generate mobile structure test and add the compact hook expectations**

Update the existing content spec so the old responsive behavior remains while the new density hooks appear:

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
    expect(page).toContain('mobile-section-strip')
    expect(panel).toContain('panel--drawer')
  })
})
```

- [ ] **Step 2: Run the generate density tests and confirm the new one fails**

Run:

```bash
npx vitest run src/views/generate-mobile-layout-content.spec.ts src/views/generate-mobile-density-content.spec.ts
```

Expected: the layout spec PASSes or stays close to green, the density spec FAILs because the compact hooks do not exist yet.

- [ ] **Step 3: Compact the section shells in `GenerateView.vue`**

Wrap mobile secondary sections in short strip containers and reduce mobile-only gaps:

```vue
<div class="preview-column">
  <ResultPreview
    :assets="platformStore.currentAssets"
    :active-index="activeIndex"
    :task="platformStore.currentTask"
    @update:active-index="activeIndex = $event"
  />

  <div v-if="isMobile" class="mobile-section-strip">
    <el-button
      v-if="workbenchSections.includes('controls')"
      class="open-parameter-button"
      type="primary"
      plain
      @click="parameterDrawerOpen = true"
    >
      打开参数面板
    </el-button>
  </div>

  <GenerationProgressCard :task="platformStore.currentTask" :audit-events="platformStore.currentTaskAudit" />
</div>
```

```css
@media (max-width: 768px) {
  .workbench {
    gap: 10px;
  }

  .preview-column,
  .side-column {
    gap: 10px;
  }

  .mobile-section-strip,
  .status-card {
    padding: 12px;
    border-radius: var(--ea-mobile-card-radius);
    box-shadow: var(--ea-mobile-card-shadow);
  }

  .status-card {
    gap: 8px;
  }

  .status-header {
    margin-bottom: 8px;
  }

  .status-title {
    font-size: 1rem;
  }

  .status-content {
    max-height: 164px;
  }
}
```

- [ ] **Step 4: Thin `ParameterPanel.vue`**

Use the existing panel, but reduce model-tip prominence and form spacing on phones:

```vue
<section class="panel panel--compact" :class="{ 'panel--drawer': $attrs.class === 'panel--drawer' }">
```

```css
.panel--compact .model-tip {
  padding: 8px 10px;
  border-radius: 12px;
}

@media (max-width: 768px) {
  .panel {
    padding: 12px;
    border-radius: var(--ea-mobile-card-radius);
    box-shadow: var(--ea-mobile-card-shadow);
  }

  .panel-header {
    margin-bottom: 8px;
  }

  .panel-title {
    font-size: 1.02rem;
  }

  .tip-text {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  :deep(.el-form-item) {
    margin-bottom: 6px;
  }
}
```

- [ ] **Step 5: Thin `ResultPreview.vue`, `GenerationProgressCard.vue`, and `ScoreRadar.vue`**

Apply explicit compact hook classes and short mobile styles:

```vue
<!-- ResultPreview.vue -->
<section class="preview-card preview-card--compact">
```

```css
@media (max-width: 768px) {
  .preview-card--compact {
    padding: 12px;
    border-radius: var(--ea-mobile-card-radius);
    box-shadow: var(--ea-mobile-card-shadow);
  }

  .image-frame {
    height: min(54vw, 260px);
    padding: 8px;
  }

  .thumb {
    width: 52px;
    height: 52px;
    border-radius: 10px;
  }
}
```

```vue
<!-- GenerationProgressCard.vue -->
<section class="progress-card progress-card--compact">
```

```css
@media (max-width: 768px) {
  .progress-card--compact {
    padding: 12px;
    border-radius: var(--ea-mobile-card-radius);
  }

  .phase-card {
    padding: 8px;
    gap: 6px;
  }

  .event-strip {
    display: grid;
    gap: 6px;
  }

  .event-chip {
    padding: 8px 10px;
    flex: initial;
  }
}
```

```vue
<!-- ScoreRadar.vue -->
<section class="score-card score-card--compact">
```

```css
@media (max-width: 768px) {
  .score-card--compact {
    padding: 12px;
    border-radius: var(--ea-mobile-card-radius);
    box-shadow: var(--ea-mobile-card-shadow);
  }

  .radar-svg {
    width: min(100%, 188px);
  }

  .metric-list {
    gap: 6px;
  }

  .metric-top {
    font-size: 0.78rem;
  }
}
```

- [ ] **Step 6: Run the generate-related suite**

Run:

```bash
npx vitest run src/views/generate-mobile-layout-content.spec.ts src/views/generate-mobile-density-content.spec.ts src/components/workbench/generation-progress.spec.ts src/components/workbench/result-preview.spec.ts src/components/workbench/score-radar.spec.ts
```

Expected: PASS with the old mobile behavior preserved and the new compact hooks present.

- [ ] **Step 7: Commit the generate density refinement**

```bash
git add web-console/src/views/GenerateView.vue web-console/src/components/workbench/ParameterPanel.vue web-console/src/components/workbench/ResultPreview.vue web-console/src/components/workbench/GenerationProgressCard.vue web-console/src/components/workbench/ScoreRadar.vue web-console/src/views/generate-mobile-layout-content.spec.ts web-console/src/views/generate-mobile-density-content.spec.ts
git commit -m "feat: flatten mobile generate workbench density"
```

## Task 4: Compress mobile history into short horizontal rows

**Files:**
- Modify: `.worktrees/electric-score-v2/web-console/src/views/HistoryView.vue`
- Modify: `.worktrees/electric-score-v2/web-console/src/components/history/HistoryFilters.vue`
- Modify: `.worktrees/electric-score-v2/web-console/src/components/history/HistoryTable.vue`
- Modify: `.worktrees/electric-score-v2/web-console/src/components/history/HistoryDetailDrawer.vue`
- Test: `.worktrees/electric-score-v2/web-console/src/components/history/history-mobile-content.spec.ts`
- Test: `.worktrees/electric-score-v2/web-console/src/components/history/history-mobile-density-content.spec.ts`
- Test: `.worktrees/electric-score-v2/web-console/src/components/history/history-detail-drawer.spec.ts`

- [ ] **Step 1: Update the existing history mobile content test to require the compact row hook too**

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
    expect(table).toContain('history-card--compact')
    expect(table).toContain('v-if="isMobile"')
    expect(filters).toContain('filters-toggle')
    expect(drawer).toContain('drawerSize')
  })
})
```

- [ ] **Step 2: Run the history tests and confirm the density one fails**

Run:

```bash
npx vitest run src/components/history/history-mobile-content.spec.ts src/components/history/history-mobile-density-content.spec.ts
```

Expected: `history-mobile-content.spec.ts` stays green or close to green, `history-mobile-density-content.spec.ts` FAILs.

- [ ] **Step 3: Compact `HistoryView.vue` and `HistoryFilters.vue`**

Make filters collapsed by default on mobile and reduce shell spacing:

```ts
// HistoryView.vue
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

const viewportWidth = ref(typeof window === 'undefined' ? 1280 : window.innerWidth)
const isMobile = computed(() => viewportWidth.value <= 768)

function syncViewport() {
  viewportWidth.value = window.innerWidth
  if (!isMobile.value) {
    filtersExpanded.value = true
  }
}

onMounted(() => window.addEventListener('resize', syncViewport))
onBeforeUnmount(() => window.removeEventListener('resize', syncViewport))
```

```ts
// set once during setup
const filtersExpanded = ref(false)
```

```css
.history-page {
  display: grid;
  gap: 16px;
}

@media (max-width: 768px) {
  .history-page {
    gap: 10px;
  }
}
```

```vue
<!-- HistoryFilters.vue -->
<section class="filters filters--compact">
```

```css
@media (max-width: 768px) {
  .filters--compact {
    padding: 12px;
    border-radius: var(--ea-mobile-card-radius);
    box-shadow: var(--ea-mobile-card-shadow);
  }

  .filters-title {
    font-size: 1rem;
  }

  .filters-header {
    margin-bottom: 10px;
  }
}
```

- [ ] **Step 4: Compact `HistoryTable.vue` and `HistoryDetailDrawer.vue`**

Turn each mobile card into a thin horizontal record:

```vue
<article v-for="row in props.items" :key="row.id" class="history-card history-card--compact" @click="emit('open', row)">
  <img class="thumb history-card__thumb" :src="buildImageUrl(row.file_path)" :alt="row.image_name" />
  <div class="history-card__body">
    <strong>{{ row.image_name }}</strong>
    <div class="history-card__meta">
      <span>{{ row.model_name }}</span>
      <span>{{ row.total_score.toFixed(2) }}</span>
      <span>{{ row.created_at }}</span>
    </div>
  </div>
</article>
```

```css
@media (max-width: 768px) {
  .table-card {
    padding: 12px;
    border-radius: var(--ea-mobile-card-radius);
    box-shadow: var(--ea-mobile-card-shadow);
  }

  .history-card--compact {
    grid-template-columns: 56px minmax(0, 1fr);
    gap: 8px;
    padding: 8px;
    border-radius: 12px;
  }

  .history-card__thumb {
    width: 56px;
    height: 56px;
    border-radius: 10px;
  }

  .history-card__body p {
    display: none;
  }
}
```

Make the detail drawer compact inside:

```vue
<div v-if="detail" class="drawer-body drawer-body--compact">
```

```css
@media (max-width: 768px) {
  .drawer-body--compact {
    gap: 12px;
  }

  .drawer-image {
    min-height: 180px;
    border-radius: 14px;
  }

  .score-chip {
    padding: 10px;
    border-radius: 12px;
  }
}
```

- [ ] **Step 5: Run the history suite**

Run:

```bash
npx vitest run src/components/history/history-mobile-content.spec.ts src/components/history/history-mobile-density-content.spec.ts src/components/history/history-detail-drawer.spec.ts
```

Expected: PASS with compact hooks present and the drawer behavior still correct.

- [ ] **Step 6: Commit the history density refinement**

```bash
git add web-console/src/views/HistoryView.vue web-console/src/components/history/HistoryFilters.vue web-console/src/components/history/HistoryTable.vue web-console/src/components/history/HistoryDetailDrawer.vue web-console/src/components/history/history-mobile-content.spec.ts web-console/src/components/history/history-mobile-density-content.spec.ts
git commit -m "feat: compact mobile history density"
```

## Task 5: Apply the same compact mobile treatment to login and overview pages

**Files:**
- Modify: `.worktrees/electric-score-v2/web-console/src/views/LoginView.vue`
- Modify: `.worktrees/electric-score-v2/web-console/src/views/DashboardView.vue`
- Modify: `.worktrees/electric-score-v2/web-console/src/views/ModelCenterView.vue`
- Modify: `.worktrees/electric-score-v2/web-console/src/views/TaskAuditView.vue`
- Modify: `.worktrees/electric-score-v2/web-console/src/views/mobile-page-layout-content.spec.ts`
- Test: `.worktrees/electric-score-v2/web-console/src/views/login-content.spec.ts`

- [ ] **Step 1: Update the broad page-layout content test to require compact mobile hooks**

```ts
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
```

- [ ] **Step 2: Run the page-level tests and confirm the compact expectations fail**

Run:

```bash
npx vitest run src/views/mobile-page-layout-content.spec.ts src/views/login-content.spec.ts
```

Expected: `login-content.spec.ts` PASS, `mobile-page-layout-content.spec.ts` FAIL because the compact hooks do not exist yet.

- [ ] **Step 3: Thin `LoginView.vue`**

Keep the login form front-and-center and demote the heavy stage content on phones:

```vue
<div class="account-hint mobile-login-summary">
  <span>默认账号：admin</span>
  <span>默认密码：admin123456</span>
</div>
```

```css
@media (max-width: 768px) {
  .lead,
  .stage-badges {
    display: none;
  }

  .status-card,
  .system-board,
  .login-shell-inner {
    border-radius: var(--ea-mobile-card-radius);
    box-shadow: var(--ea-mobile-card-shadow);
  }

  .status-card,
  .board-row,
  .account-hint span {
    padding-block: 8px;
  }

  .shell-header h2 {
    font-size: 1.5rem;
  }
}
```

- [ ] **Step 4: Thin `DashboardView.vue`, `ModelCenterView.vue`, and `TaskAuditView.vue`**

Apply the same compact mobile class to summary shells and reduce vertical spacing:

```vue
<!-- representative pattern -->
<article class="summary-card mobile-compact-card">
  ...
</article>
```

```css
@media (max-width: 768px) {
  .mobile-compact-card {
    padding: 12px;
    border-radius: var(--ea-mobile-card-radius);
    box-shadow: var(--ea-mobile-card-shadow);
  }

  .hero,
  .summary-grid,
  .content-grid,
  .model-grid {
    gap: 10px;
  }
}
```

- [ ] **Step 5: Run the page-level suite**

Run:

```bash
npx vitest run src/views/mobile-page-layout-content.spec.ts src/views/login-content.spec.ts
```

Expected: PASS with the broad mobile coverage intact and the new compact hooks present.

- [ ] **Step 6: Commit the remaining mobile density refinement**

```bash
git add web-console/src/views/LoginView.vue web-console/src/views/DashboardView.vue web-console/src/views/ModelCenterView.vue web-console/src/views/TaskAuditView.vue web-console/src/views/mobile-page-layout-content.spec.ts
git commit -m "feat: compact remaining mobile page density"
```

## Task 6: Run verification and capture the final state

**Files:**
- Modify: `.worktrees/electric-score-v2/docs/superpowers/plans/2026-04-08-web-console-mobile-density.md`
  Mark completed checkboxes during execution.

- [ ] **Step 1: Run the focused mobile suite**

Run:

```bash
npx vitest run src/components/app-shell-content.spec.ts src/components/app-shell-density-content.spec.ts src/views/mobile-page-layout-content.spec.ts src/views/generate-mobile-layout-content.spec.ts src/views/generate-mobile-density-content.spec.ts src/components/history/history-mobile-content.spec.ts src/components/history/history-mobile-density-content.spec.ts src/views/login-content.spec.ts src/components/workbench/generation-progress.spec.ts src/components/workbench/result-preview.spec.ts src/components/workbench/score-radar.spec.ts src/components/history/history-detail-drawer.spec.ts
```

Expected: PASS with all old responsive tests and new density tests green.

- [ ] **Step 2: Run the production build**

Run:

```bash
npm run build
```

Expected: PASS with Vite producing the `dist/` bundle and no template/type errors.

- [ ] **Step 3: Review the diff**

Run:

```bash
git status --short
```

Expected: only the planned `web-console` source files and this plan file are modified, plus the known unrelated `python-ai-service/.idea/` remains untouched.

- [ ] **Step 4: Commit the completed mobile density refinement**

```bash
git add web-console/src/App.vue web-console/src/components/AppShell.vue web-console/src/components/app-shell-content.spec.ts web-console/src/components/app-shell-density-content.spec.ts web-console/src/components/history/HistoryDetailDrawer.vue web-console/src/components/history/HistoryFilters.vue web-console/src/components/history/HistoryTable.vue web-console/src/components/history/history-mobile-content.spec.ts web-console/src/components/history/history-mobile-density-content.spec.ts web-console/src/components/workbench/GenerationProgressCard.vue web-console/src/components/workbench/ParameterPanel.vue web-console/src/components/workbench/ResultPreview.vue web-console/src/components/workbench/ScoreRadar.vue web-console/src/views/DashboardView.vue web-console/src/views/GenerateView.vue web-console/src/views/HistoryView.vue web-console/src/views/LoginView.vue web-console/src/views/ModelCenterView.vue web-console/src/views/TaskAuditView.vue web-console/src/views/generate-mobile-layout-content.spec.ts web-console/src/views/generate-mobile-density-content.spec.ts web-console/src/views/mobile-page-layout-content.spec.ts
git commit -m "feat: refine mobile density across web console"
```

## Self-Review

### Spec coverage

- The thinner mobile shell, top bar, and bottom navigation are covered by Task 2.
- The generate page requirement to replace tall cards with short modules is covered by Task 3.
- The history requirement to replace big cards with short horizontal rows is covered by Task 4.
- The login, dashboard, model center, and task audit mobile compacting is covered by Task 5.
- Focused regression verification and a production build are covered by Task 6.

No spec section is left without a task.

### Placeholder scan

- No `TODO`, `TBD`, or “similar to Task N” placeholders remain.
- Every task includes concrete file paths, code snippets, test commands, and expected outputs.

### Type consistency

- The new compact hook names are used consistently: `topbar-status-dot`, `mobile-nav-text`, `mobile-section-strip`, `preview-card--compact`, `progress-card--compact`, `score-card--compact`, `filters--compact`, `history-card--compact`, `drawer-body--compact`, `mobile-login-summary`, and `mobile-compact-card`.
- Existing responsive hooks such as `parameter-drawer`, `open-parameter-button`, `filters-toggle`, and `drawerSize` are preserved rather than renamed.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-08-web-console-mobile-density.md`.

Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Because you already asked me to make the follow-up decisions, the next step should use **Inline Execution**.
