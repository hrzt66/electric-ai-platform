# Result Preview Fixed Frame Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将生成结果主图收敛到“多图预览”卡片内的固定预览框中，同时保留点击主图弹出大图预览的能力。

**Architecture:** 仅调整 `ResultPreview.vue` 的模板结构与样式层级，不改动生成页三列布局，也不新增全屏覆盖逻辑。先用 SSR 组件测试锁定预览框与 `el-image` 预览参数，再用最小模板改动实现固定预览框。

**Tech Stack:** Vue 3、TypeScript、Vitest、Vite SSR

---

### Task 1: 为结果预览补组件结构测试

**Files:**
- Create: `E:\毕业设计\golang-毕业设计\.worktrees\vertical-slice-foundation\web-console\src\components\workbench\result-preview.spec.ts`

- [ ] **Step 1: 编写失败测试，锁定固定预览框结构**

```ts
expect(html).toContain('class="image-frame"')
expect(html).toContain('data-preview-count="2"')
expect(html).toContain('data-initial-index="1"')
```

- [ ] **Step 2: 运行单测并确认先失败**

Run: `cd web-console; npx vitest run src/components/workbench/result-preview.spec.ts`

Expected: FAIL，提示结果模板中缺少 `image-frame` 固定预览框结构。

### Task 2: 实现固定预览框与弹层大图

**Files:**
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\vertical-slice-foundation\web-console\src\components\workbench\ResultPreview.vue`

- [ ] **Step 1: 在主图外层增加固定预览框容器**

```vue
<div class="image-frame">
  <el-image
    class="main-image"
    :src="buildImageUrl(activeAsset.file_path)"
    fit="contain"
    :preview-src-list="assets.map((item) => buildImageUrl(item.file_path))"
    :initial-index="activeIndex"
  />
</div>
```

- [ ] **Step 2: 收紧卡片内部布局高度**

```css
.image-stage {
  align-content: start;
  grid-template-rows: auto auto auto;
}

.image-frame {
  height: clamp(220px, 30vh, 320px);
  padding: 12px;
  border-radius: 18px;
  overflow: hidden;
}
```

- [ ] **Step 3: 运行单测并确认转绿**

Run: `cd web-console; npx vitest run src/components/workbench/result-preview.spec.ts`

Expected: PASS，说明固定预览框与大图预览参数同时保留。

### Task 3: 进行前端回归验证

**Files:**
- Verify: `E:\毕业设计\golang-毕业设计\.worktrees\vertical-slice-foundation\web-console\src\components\workbench\ResultPreview.vue`
- Verify: `E:\毕业设计\golang-毕业设计\.worktrees\vertical-slice-foundation\web-console\src\views\GenerateView.vue`

- [ ] **Step 1: 跑完整前端测试**

Run: `npm --prefix web-console run test`

Expected: PASS，已有工作台与路由测试不回归。

- [ ] **Step 2: 跑构建验证**

Run: `npm --prefix web-console run build`

Expected: PASS，Vite 构建成功且无新增编译错误。
