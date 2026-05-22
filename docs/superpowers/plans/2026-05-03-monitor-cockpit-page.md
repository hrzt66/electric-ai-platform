# Monitor Cockpit Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dedicated AI monitor cockpit page with circular percentage indicators, explicit missing-data explanations, and shell navigation entry while keeping the dashboard as a lighter summary.

**Architecture:** Add a new authenticated `/monitor` route backed by a dedicated `MonitorCockpitView.vue`, derive display-ready monitor metrics from the existing `platformStore.monitorOverview`, and expose missing-data reasons through view-level helpers instead of changing backend contracts. Keep the app shell responsible for navigation, and cover the new behavior with route, shell, and cockpit-specific tests.

**Tech Stack:** Vue 3, Pinia, Vue Router, Vitest, Vite, scoped CSS

---

## File Structure

- Create: `web-console/src/views/MonitorCockpitView.vue`
- Create: `web-console/src/views/MonitorCockpitView.spec.ts`
- Modify: `web-console/src/router/index.ts`
- Modify: `web-console/src/router/index.spec.ts`
- Modify: `web-console/src/components/AppShell.vue`
- Modify: `web-console/src/components/app-shell-layout.spec.ts`
- Modify: `web-console/src/views/DashboardView.vue`
- Modify: `web-console/src/views/DashboardView.spec.ts`

### Task 1: Add Failing Route And Shell Navigation Tests

**Files:**
- Modify: `web-console/src/router/index.spec.ts`
- Modify: `web-console/src/components/app-shell-layout.spec.ts`
- Test: `web-console/src/router/index.spec.ts`
- Test: `web-console/src/components/app-shell-layout.spec.ts`

- [ ] **Step 1: Write the failing route test for the new monitor page**

```ts
it('allows authenticated users to open the monitor cockpit route', async () => {
  const { createAppRouter } = await import('./index')
  const router = createAppRouter(createMemoryHistory())
  const authStore = useAuthStore()
  authStore.setSession({
    accessToken: 'token-123',
    userName: 'admin',
    displayName: '系统管理员',
  })

  await router.push('/monitor')

  expect(router.currentRoute.value.path).toBe('/monitor')
})
```

- [ ] **Step 2: Write the failing shell navigation assertion**

```ts
it('includes a dedicated monitor navigation entry', () => {
  const content = readFileSync(resolve(__dirname, './AppShell.vue'), 'utf8')

  expect(content).toContain("label: '运行监控'")
  expect(content).toContain("path: '/monitor'")
  expect(content).toContain("hint: 'Monitor'")
})
```

- [ ] **Step 3: Run the targeted tests to verify RED**

Run: `npm --prefix web-console run test -- src/router/index.spec.ts src/components/app-shell-layout.spec.ts`

Expected: FAIL because `/monitor` route and monitor nav item do not exist yet.

- [ ] **Step 4: Implement the minimal router and shell navigation changes**

```ts
// web-console/src/router/index.ts
import MonitorCockpitView from '../views/MonitorCockpitView.vue'

// children
{ path: 'monitor', component: MonitorCockpitView },
```

```ts
// web-console/src/components/AppShell.vue
const navItems = [
  { label: '平台总览', path: '/dashboard', hint: 'Dashboard' },
  { label: '运行监控', path: '/monitor', hint: 'Monitor' },
  { label: '生成工作台', path: '/generate', hint: 'Generate' },
  { label: '历史中心', path: '/history', hint: 'History' },
  { label: '模型中心', path: '/models', hint: 'Models' },
  { label: '任务审计', path: '/tasks/audit', hint: 'Audit' },
]
```

- [ ] **Step 5: Run the targeted tests to verify GREEN**

Run: `npm --prefix web-console run test -- src/router/index.spec.ts src/components/app-shell-layout.spec.ts`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add web-console/src/router/index.ts web-console/src/router/index.spec.ts web-console/src/components/AppShell.vue web-console/src/components/app-shell-layout.spec.ts
git commit -m "feat: add monitor cockpit navigation"
```

### Task 2: Add Failing Cockpit View Tests

**Files:**
- Create: `web-console/src/views/MonitorCockpitView.spec.ts`
- Test: `web-console/src/views/MonitorCockpitView.spec.ts`

- [ ] **Step 1: Write the failing monitor cockpit render test for populated data**

```ts
it('renders circular metrics and detailed monitor sections when data exists', async () => {
  platformStore.monitorConnected = true
  platformStore.monitorOverview = {
    overall_health: 'warning',
    host_snapshot: {
      platform_family: 'macos',
      cpu_usage_percent: 72,
      memory_total_bytes: 100,
      memory_used_bytes: 58,
      memory_pressure_level: 'warning',
    },
    accelerator_snapshot: {
      accelerator_type: 'apple-mps',
      summary_label: 'AI 加速资源健康',
      available: true,
      gpu_utilization_percent: 41,
      unified_memory_pressure: 'warning',
    },
    service_snapshots: [
      { service_name: 'gateway-service', status: 'running' },
      { service_name: 'python-ai-service', status: 'running' },
    ],
    task_runtime_context: {
      active_task_count: 2,
      latest_task_stage: 'scoring',
    },
    active_alerts: [{ alert_id: 'a1', level: 'warning', title: '统一内存压力偏高' }],
    recent_alerts: [{ alert_id: 'a2', level: 'warning', title: '阶段上报延迟' }],
  }

  const html = await renderView()

  expect(html).toContain('AI 运行监控驾驶舱')
  expect(html).toContain('72%')
  expect(html).toContain('58%')
  expect(html).toContain('41%')
  expect(html).toContain('gateway-service')
  expect(html).toContain('python-ai-service')
  expect(html).toContain('统一内存压力偏高')
  expect(html).toContain('阶段上报延迟')
})
```

- [ ] **Step 2: Write the failing missing-data explanation test**

```ts
it('explains why monitor data is missing instead of showing fake zeroes', async () => {
  platformStore.monitorConnected = false
  platformStore.monitorOverview = {
    overall_health: 'critical',
    host_snapshot: { platform_family: 'macos', cpu_usage_percent: 0 },
    accelerator_snapshot: {
      accelerator_type: 'unavailable',
      summary_label: '不可用',
      available: false,
      unavailable_reason: '当前设备未启用可用 AI 加速器',
    },
    service_snapshots: [],
    task_runtime_context: { active_task_count: 0 },
    active_alerts: [],
    recent_alerts: [],
  }

  const html = await renderView()

  expect(html).toContain('当前没有运行任务，因此没有最新阶段上报')
  expect(html).toContain('尚未收到关键服务快照')
  expect(html).toContain('当前设备未启用可用 AI 加速器')
  expect(html).not.toContain('内存 0%')
  expect(html).not.toContain('GPU 0%')
})
```

- [ ] **Step 3: Run the targeted tests to verify RED**

Run: `npm --prefix web-console run test -- src/views/MonitorCockpitView.spec.ts`

Expected: FAIL because the view file does not exist yet.

- [ ] **Step 4: Commit the failing tests once they are in place**

```bash
git add web-console/src/views/MonitorCockpitView.spec.ts
git commit -m "test: cover monitor cockpit view"
```

### Task 3: Implement The Monitor Cockpit View

**Files:**
- Create: `web-console/src/views/MonitorCockpitView.vue`
- Test: `web-console/src/views/MonitorCockpitView.spec.ts`

- [ ] **Step 1: Create the minimal view structure to satisfy the new route**

```vue
<template>
  <div class="monitor-cockpit">
    <section class="cockpit-hero">
      <h2>AI 运行监控驾驶舱</h2>
    </section>
  </div>
</template>
```

- [ ] **Step 2: Run the cockpit test to see the next expected failure**

Run: `npm --prefix web-console run test -- src/views/MonitorCockpitView.spec.ts`

Expected: FAIL on missing percentages and missing explanation copy.

- [ ] **Step 3: Implement derived monitor helpers and the resource ring cards**

```ts
const memoryPercent = computed(() => {
  const host = platformStore.monitorOverview?.host_snapshot
  if (
    typeof host?.memory_total_bytes !== 'number' ||
    typeof host?.memory_used_bytes !== 'number' ||
    host.memory_total_bytes <= 0
  ) {
    return null
  }
  return Math.round((host.memory_used_bytes / host.memory_total_bytes) * 100)
})

const acceleratorPercent = computed(() => {
  const accelerator = platformStore.monitorOverview?.accelerator_snapshot
  if (typeof accelerator?.gpu_utilization_percent === 'number') {
    return Math.round(accelerator.gpu_utilization_percent)
  }
  if (
    typeof accelerator?.vram_total_mb === 'number' &&
    typeof accelerator?.vram_used_mb === 'number' &&
    accelerator.vram_total_mb > 0
  ) {
    return Math.round((accelerator.vram_used_mb / accelerator.vram_total_mb) * 100)
  }
  return null
})
```

```vue
<article class="ring-card">
  <div class="ring" :style="{ '--ring-percent': `${cpuPercent ?? 0}%` }">
    <div class="ring-core">{{ cpuPercent == null ? 'N/A' : `${cpuPercent}%` }}</div>
  </div>
  <strong>CPU</strong>
  <small>{{ cpuExplanation }}</small>
</article>
```

- [ ] **Step 4: Implement the missing-data explanation panel, service matrix, and task flow panel**

```ts
const missingReasons = computed(() => {
  const overview = platformStore.monitorOverview
  const reasons: string[] = []

  if ((overview?.task_runtime_context?.active_task_count ?? 0) === 0 && !overview?.task_runtime_context?.latest_task_stage) {
    reasons.push('当前没有运行任务，因此没有最新阶段上报')
  }

  if ((overview?.service_snapshots?.length ?? 0) === 0) {
    reasons.push('尚未收到关键服务快照，说明服务探针尚未返回')
  }

  const accelerator = overview?.accelerator_snapshot
  if (accelerator?.accelerator_type === 'unavailable' && accelerator.unavailable_reason) {
    reasons.push(accelerator.unavailable_reason)
  }

  if (memoryPercent.value == null) {
    reasons.push('监控服务尚未提供内存占用字段')
  }

  return reasons
})
```

- [ ] **Step 5: Run the cockpit test to verify GREEN**

Run: `npm --prefix web-console run test -- src/views/MonitorCockpitView.spec.ts`

Expected: PASS

- [ ] **Step 6: Refactor only if needed, then re-run the same cockpit test**

Run: `npm --prefix web-console run test -- src/views/MonitorCockpitView.spec.ts`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add web-console/src/views/MonitorCockpitView.vue web-console/src/views/MonitorCockpitView.spec.ts
git commit -m "feat: add monitor cockpit view"
```

### Task 4: Add Dashboard Entry And Summary Adjustments

**Files:**
- Modify: `web-console/src/views/DashboardView.spec.ts`
- Modify: `web-console/src/views/DashboardView.vue`
- Test: `web-console/src/views/DashboardView.spec.ts`

- [ ] **Step 1: Write the failing dashboard entry test**

```ts
it('links the monitor summary area to the dedicated cockpit page', async () => {
  platformStore.monitorOverview = {
    overall_health: 'warning',
    host_snapshot: { platform_family: 'macos', cpu_usage_percent: 22 },
    accelerator_snapshot: null,
    service_snapshots: [],
    task_runtime_context: { active_task_count: 0 },
    active_alerts: [],
    recent_alerts: [],
  }

  const html = await renderView()

  expect(html).toContain('进入监控驾驶舱')
  expect(html).toContain('/monitor')
})
```

- [ ] **Step 2: Run the dashboard test to verify RED**

Run: `npm --prefix web-console run test -- src/views/DashboardView.spec.ts`

Expected: FAIL because the entry link does not exist yet.

- [ ] **Step 3: Add the minimal dashboard entry and tighten summary copy**

```vue
<div class="monitor-header-actions">
  <router-link class="monitor-link" to="/monitor">进入监控驾驶舱</router-link>
</div>
```

- [ ] **Step 4: Run the dashboard test to verify GREEN**

Run: `npm --prefix web-console run test -- src/views/DashboardView.spec.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web-console/src/views/DashboardView.vue web-console/src/views/DashboardView.spec.ts
git commit -m "feat: link dashboard monitor summary to cockpit"
```

### Task 5: Full Verification

**Files:**
- Modify: `web-console/src/router/index.ts`
- Modify: `web-console/src/router/index.spec.ts`
- Modify: `web-console/src/components/AppShell.vue`
- Modify: `web-console/src/components/app-shell-layout.spec.ts`
- Modify: `web-console/src/views/DashboardView.vue`
- Modify: `web-console/src/views/DashboardView.spec.ts`
- Create: `web-console/src/views/MonitorCockpitView.vue`
- Create: `web-console/src/views/MonitorCockpitView.spec.ts`

- [ ] **Step 1: Run the focused frontend test suite**

Run: `npm --prefix web-console run test -- src/router/index.spec.ts src/components/app-shell-layout.spec.ts src/views/DashboardView.spec.ts src/views/MonitorCockpitView.spec.ts`

Expected: PASS

- [ ] **Step 2: Run the production build**

Run: `npm --prefix web-console run build`

Expected: exit code 0

- [ ] **Step 3: Review the plan requirements against the final diff**

Checklist:
- Dedicated `/monitor` page exists
- Shell nav includes `运行监控`
- Cockpit shows rings for real percentages
- Cockpit explains missing values without fake zeroes
- Dashboard links to cockpit instead of carrying full detail

- [ ] **Step 4: Commit the integrated result if previous task commits were not used**

```bash
git status --short
```

Expected: only intended frontend files remain modified.
