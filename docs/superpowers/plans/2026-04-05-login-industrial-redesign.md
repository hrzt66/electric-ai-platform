# Login Industrial Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `web-console` 登录页重构为工业控制中心风入口页，同时保留现有真实登录逻辑和跳转行为。

**Architecture:** 仅重构登录页单一入口，不改后端接口。通过重写 `LoginView.vue` 的内容结构与样式层次，强化平台感、工业感和信息表达，同时确保表单、错误提示、跳转逻辑继续工作。

**Tech Stack:** Vue 3、TypeScript、Element Plus、Vite

---

### Task 1: 重写登录页内容与布局

**Files:**
- Modify: `E:\毕业设计\golang-毕业设计\.worktrees\vertical-slice-foundation\web-console\src\views\LoginView.vue`

- [ ] **Step 1: 确认当前登录页问题点**

检查以下问题：

- 文案存在乱码
- 左右信息层次不足
- 平台能力展示不够像工业入口
- 卡片和背景关系偏普通

- [ ] **Step 2: 重写页面结构**

将页面组织为：

- 左侧：平台标题、说明、三张能力卡片
- 右侧：登录卡、错误提示、账号密码输入、登录按钮

- [ ] **Step 3: 保留登录逻辑**

继续保留：

- `http.post('/auth/login', form)`
- `authStore.setSession(...)`
- `router.push(redirectPath.value)`
- `ElMessage.success / ElMessage.error`

- [ ] **Step 4: 重写视觉样式**

样式要求：

- 工业蓝灰 + 铜金强调
- 大面积深色背景
- 登录卡片具有入口感
- 桌面双栏，移动端单栏

- [ ] **Step 5: 运行构建验证**

Run: `npm --prefix web-console run build`

Expected:

- 构建成功
- 登录页组件无语法错误

### Task 2: 结果自检

**Files:**
- Verify: `E:\毕业设计\golang-毕业设计\.worktrees\vertical-slice-foundation\web-console\src\views\LoginView.vue`

- [ ] **Step 1: 检查文案编码**

确认登录页源文件中的中文都是正常可读文本，而不是乱码。

- [ ] **Step 2: 检查布局退化**

确认存在移动端媒体查询，窄屏时从双栏切为单栏。

- [ ] **Step 3: 检查交互保持不变**

确认 loading、错误提示、成功跳转仍保留。
