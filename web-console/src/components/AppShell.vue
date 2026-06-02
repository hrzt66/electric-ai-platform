<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const navigating = ref(false)

const navItems = [
  { label: '平台总览', path: '/dashboard', hint: 'Dashboard' },
  { label: '生成工作台', path: '/generate', hint: 'Generate' },
  { label: '历史中心', path: '/history', hint: 'History' },
  { label: '模型中心', path: '/models', hint: 'Models' },
  { label: '任务审计', path: '/tasks/audit', hint: 'Audit' },
]

const activePath = computed(() => navItems.find((item) => route.path.startsWith(item.path))?.path ?? '/dashboard')
const currentTitle = computed(() => navItems.find((item) => item.path === activePath.value)?.label ?? '工业工作台')

async function go(path: string) {
  if (path === route.path || navigating.value) {
    return
  }

  navigating.value = true
  try {
    await router.push(path)
  } finally {
    navigating.value = false
  }
}

function logout() {
  authStore.clearSession()
  router.push('/login')
}
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">EA</div>
        <div class="brand-copy">
          <p class="brand-kicker">Unified Console</p>
          <p class="brand-title">Electric AI</p>
          <p class="brand-subtitle">生成与评分统一平台</p>
        </div>
      </div>

      <nav class="nav">
        <button
          v-for="item in navItems"
          :key="item.path"
          class="nav-item"
          :class="{ active: item.path === activePath }"
          type="button"
          :disabled="item.path === activePath || navigating"
          @click="go(item.path)"
        >
          <span class="nav-label">{{ item.label }}</span>
          <span class="nav-path">{{ item.hint }}</span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <div class="user-card">
          <p class="user-label">当前账号</p>
          <p class="user-name">{{ authStore.displayName || authStore.userName || '未登录' }}</p>
        </div>
        <el-button plain class="logout-button" @click="logout">退出登录</el-button>
      </div>
    </aside>

    <div class="content">
      <header class="topbar">
        <div class="topbar-copy">
          <p class="eyebrow">统一平台</p>
          <h1 class="page-title">{{ currentTitle }}</h1>
          <p class="topbar-description">面向生成、评分、审计与服务编排的一体化控制台入口</p>
        </div>
        <div class="topbar-badge">
          <span class="badge-dot" />
          生成、评分 / 服务编排 / 审计追踪
        </div>
      </header>

      <main class="main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell {
  --line-500: #d9e2ec;
  --text-100: #0f172a;
  --text-200: #334155;
  --text-300: #64748b;
  --accent-500: #1d4ed8;
  --accent-600: #1e3a8a;
  height: 100vh;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  overflow: hidden;
  background:
    radial-gradient(circle at 14% 16%, rgba(29, 78, 216, 0.05), transparent 24%),
    linear-gradient(135deg, #eef3f9 0%, #f6f8fb 46%, #f8fafc 100%);
}

.sidebar {
  height: 100vh;
  padding: 22px 18px 18px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.98), rgba(241, 245, 249, 0.98));
  backdrop-filter: blur(14px);
  color: var(--text-100);
  border-right: 1px solid var(--line-500);
  box-shadow: inset -1px 0 0 rgba(255, 255, 255, 0.72);
}

.brand {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 6px 4px 2px;
}

.brand-mark {
  width: 50px;
  height: 50px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--text-100);
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  border: 1px solid #bfdbfe;
  box-shadow:
    0 10px 24px rgba(15, 23, 42, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.62);
}

.brand-copy {
  display: grid;
  gap: 3px;
}

.brand-title,
.brand-subtitle,
.brand-kicker,
.user-label,
.user-name,
.eyebrow,
.page-title,
.topbar-description {
  margin: 0;
}

.brand-kicker {
  color: var(--accent-600);
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.brand-title {
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.brand-subtitle {
  color: var(--text-300);
  font-size: 0.82rem;
  line-height: 1.45;
}

.nav {
  display: grid;
  gap: 10px;
}

.nav-item {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 13px 14px;
  text-align: left;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(248, 250, 252, 0.98));
  color: inherit;
  cursor: pointer;
  transition:
    transform 0.2s ease,
    background 0.2s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

.nav-item:disabled {
  cursor: default;
  opacity: 0.96;
}

.nav-item:hover,
.nav-item.active {
  transform: translateX(4px);
  background: linear-gradient(90deg, rgba(219, 234, 254, 0.96), rgba(239, 246, 255, 0.98));
  border-color: rgba(29, 78, 216, 0.24);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.56),
    0 12px 24px rgba(15, 23, 42, 0.08);
}

.nav-label,
.nav-path {
  display: block;
}

.nav-label {
  font-size: 0.94rem;
  font-weight: 600;
}

.nav-path {
  margin-top: 3px;
  color: var(--text-300);
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.11em;
}

.sidebar-footer {
  margin-top: auto;
  display: grid;
  gap: 12px;
}

.user-card {
  padding: 14px;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  border: 1px solid var(--line-500);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.64);
}

.user-label {
  color: var(--text-300);
  font-size: 0.76rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.user-name {
  margin-top: 5px;
  font-size: 0.96rem;
  font-weight: 600;
  color: var(--text-100);
}

.logout-button {
  width: 100%;
  border-color: #cbd5e1;
  background: #ffffff;
  color: var(--text-100);
}

.content {
  height: 100vh;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.38), rgba(255, 255, 255, 0)),
    linear-gradient(180deg, rgba(248, 250, 252, 0.92), rgba(243, 246, 250, 0.96));
}

.topbar {
  margin: 18px 18px 0;
  padding: 18px 20px 16px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  border: 1px solid var(--line-500);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.72),
    0 18px 36px rgba(15, 23, 42, 0.08);
}

.topbar-copy {
  display: grid;
  gap: 5px;
}

.eyebrow {
  color: var(--accent-600);
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.16em;
}

.page-title {
  color: var(--text-100);
  font-size: clamp(1.65rem, 1.9vw, 2.2rem);
  font-weight: 700;
  letter-spacing: 0.02em;
}

.topbar-description {
  color: var(--text-300);
  font-size: 0.92rem;
  line-height: 1.55;
}

.topbar-badge {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 9px 14px;
  border-radius: 999px;
  background: #f8fafc;
  border: 1px solid var(--line-500);
  color: var(--text-200);
  font-size: 0.82rem;
  white-space: nowrap;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

.badge-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--accent-500);
  box-shadow: 0 0 0 6px rgba(29, 78, 216, 0.12);
}

.main {
  min-width: 0;
  min-height: 0;
  padding: 18px;
}

@media (max-width: 1100px) {
  .shell {
    height: auto;
    min-height: 100vh;
    grid-template-columns: 1fr;
    overflow: visible;
    background:
      radial-gradient(circle at 18% 10%, rgba(29, 78, 216, 0.06), transparent 24%),
      linear-gradient(180deg, #eef3f9 0%, #f8fafc 100%);
  }

  .sidebar {
    height: auto;
    padding-bottom: 12px;
    overflow: visible;
  }

  .nav {
    grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  }

  .content {
    height: auto;
    overflow: visible;
  }

  .topbar {
    margin-top: 0;
    flex-direction: column;
    align-items: stretch;
  }

  .topbar-badge {
    white-space: normal;
  }
}
</style>
