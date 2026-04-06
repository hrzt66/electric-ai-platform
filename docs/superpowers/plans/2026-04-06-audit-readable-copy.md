# Audit Readable Copy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将前端审计事件展示统一升级为中文标题与中文说明，并接入生成页、任务审计页和历史详情抽屉三个入口。

**Architecture:** 新增一个审计事件展示格式化器负责解析 `payload_json`、翻译事件标题和生成中文说明；再新增一个共用 `AuditTimeline` 组件统一渲染时间线，三处页面全部切换到该组件，彻底去掉原始 JSON 直出。

**Tech Stack:** Vue 3、TypeScript、Element Plus、Vitest、Vite SSR

---

### Task 1: 为审计中文化展示补失败测试

**Files:**
- Create: `E:\毕业设计\golang-毕业设计\.worktrees\vertical-slice-foundation\web-console\src\components\audit\audit-event-presenter.spec.ts`

- [ ] **Step 1: 编写失败测试，锁定核心事件的中文标题与说明**

```ts
expect(presentAuditEvent(createEvent('task.preparing', '{"job_id":6,"model_name":"sd15-electric"}'))).toEqual({
  title: '任务已受理',
  description: '系统已接收任务，正在为模型 sd15-electric 准备运行环境。',
})
```

- [ ] **Step 2: 运行单测并确认先失败**

Run: `cd web-console; npx vitest run src/components/audit/audit-event-presenter.spec.ts`

Expected: FAIL，提示审计展示器模块不存在或中文映射缺失。

### Task 2: 实现共用审计展示器与时间线组件

**Files:**
- Create: `E:\毕业设计\golang-毕业设计\.worktrees\vertical-slice-foundation\web-console\src\components\audit\audit-event-presenter.ts`
- Create: `E:\毕业设计\golang-毕业设计\.worktrees\vertical-slice-foundation\web-console\src\components\audit\AuditTimeline.vue`

- [ ] **Step 1: 实现 payload 解析与中文文案生成**

```ts
export function presentAuditEvent(event: AuditEvent): PresentedAuditEvent {
  const payload = parsePayload(event.payload_json)
  return {
    title: resolveTitle(event.event_type),
    description: resolveDescription(event.event_type, payload, event.message),
  }
}
```

- [ ] **Step 2: 实现共用时间线组件**

```vue
<el-empty v-if="events.length === 0" :description="emptyDescription" />
<el-timeline v-else>
  <el-timeline-item v-for="event in presentedEvents" :key="event.id" :timestamp="event.created_at" placement="top">
    <strong>{{ event.title }}</strong>
    <p class="timeline-body">{{ event.description }}</p>
  </el-timeline-item>
</el-timeline>
```

- [ ] **Step 3: 运行单测并确认转绿**

Run: `cd web-console; npx vitest run src/components/audit/audit-event-presenter.spec.ts`

Expected: PASS，说明核心事件已能输出中文标题与中文说明。

### Task 3: 接入三个页面并回归验证

**Files:**
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\vertical-slice-foundation\web-console\src\views\GenerateView.vue`
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\vertical-slice-foundation\web-console\src\views\TaskAuditView.vue`
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\vertical-slice-foundation\web-console\src\components\history\HistoryDetailDrawer.vue`

- [ ] **Step 1: 用共用时间线组件替换三处原有直出模板**

```vue
<AuditTimeline :events="platformStore.currentTaskAudit" empty-description="当前还没有可展示的审计事件。" />
```

- [ ] **Step 2: 跑完整前端测试**

Run: `npm --prefix web-console run test`

Expected: PASS，已有前端测试与新增审计展示测试全部通过。

- [ ] **Step 3: 跑构建验证**

Run: `npm --prefix web-console run build`

Expected: PASS，Vite 构建成功且无新增编译错误。
