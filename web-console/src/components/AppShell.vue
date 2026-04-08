<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import { MOBILE_BREAKPOINT } from '../utils/mobile-layout'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const navigating = ref(false)
const viewportWidth = ref(typeof window === 'undefined' ? 1280 : window.innerWidth)
const mobileMenuOpen = ref(false)

// 左侧导航集中维护在这里，页面标题与高亮状态都从同一份配置推导。
const navItems = [
  { label: '平台总览', path: '/dashboard', hint: 'Dashboard' },
  { label: '生成工作台', path: '/generate', hint: 'Generate' },
  { label: '历史中心', path: '/history', hint: 'History' },
  { label: '模型中心', path: '/models', hint: 'Models' },
  { label: '任务审计', path: '/tasks/audit', hint: 'Audit' },
]

const isMobile = computed(() => viewportWidth.value <= MOBILE_BREAKPOINT)
const activePath = computed(() => navItems.find((item) => route.path.startsWith(item.path))?.path ?? '/dashboard')
const currentTitle = computed(() => navItems.find((item) => item.path === activePath.value)?.label ?? '工业工作台')

function syncViewport() {
  viewportWidth.value = window.innerWidth
  if (!isMobile.value) {
    mobileMenuOpen.value = false
  }
}

async function go(path: string) {
  // 通过 navigating 锁避免用户快速连点导航时重复 push，减少页面闪烁和竞态。
  if (path === route.path || navigating.value) {
    mobileMenuOpen.value = false
    return
  }

  navigating.value = true
  try {
    await router.push(path)
  } finally {
    navigating.value = false
    mobileMenuOpen.value = false
  }
}

function logout() {
  authStore.clearSession()
  mobileMenuOpen.value = false
  router.push('/login')
}

onMounted(() => {
  window.addEventListener('resize', syncViewport)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncViewport)
})
</script>

<template>
  <div class="shell" :class="{ 'shell-mobile': isMobile }">
    <aside v-if="!isMobile" class="sidebar">
      <div class="brand">
        <div class="brand-mark">EA</div>
        <div>
          <p class="brand-title">Electric AI</p>
          <p class="brand-subtitle">工业图像生成与评分平台</p>
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
      <header class="topbar" :class="{ 'topbar-mobile': isMobile }">
        <div class="topbar-main">
          <button v-if="isMobile" class="menu-button" type="button" aria-label="打开导航菜单" @click="mobileMenuOpen = true">
            <span />
            <span />
            <span />
          </button>

          <div>
            <p v-if="!isMobile" class="eyebrow">本机原生运行时</p>
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

      <main class="main">
        <router-view />
      </main>
    </div>

    <el-drawer
      v-model="mobileMenuOpen"
      class="mobile-shell-drawer"
      direction="ltr"
      size="min(86vw, 320px)"
      :with-header="false"
      append-to-body
    >
      <div class="drawer-shell">
        <div class="brand">
          <div class="brand-mark">EA</div>
          <div>
            <p class="brand-title">Electric AI</p>
            <p class="brand-subtitle brand-subtitle-dark">工业图像生成与评分平台</p>
          </div>
        </div>

        <nav class="drawer-nav">
          <button
            v-for="item in navItems"
            :key="item.path"
            class="nav-item nav-item-dark"
            :class="{ active: item.path === activePath }"
            type="button"
            :disabled="item.path === activePath || navigating"
            @click="go(item.path)"
          >
            <span class="nav-label">{{ item.label }}</span>
            <span class="nav-path nav-path-dark">{{ item.hint }}</span>
          </button>
        </nav>

        <div class="drawer-footer">
          <div class="user-card user-card-dark">
            <p class="user-label">当前账号</p>
            <p class="user-name">{{ authStore.displayName || authStore.userName || '未登录' }}</p>
          </div>
          <el-button plain class="logout-button" @click="logout">退出登录</el-button>
        </div>
      </div>
    </el-drawer>

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
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  background:
    radial-gradient(circle at top left, rgba(211, 164, 73, 0.18), transparent 26%),
    linear-gradient(180deg, #0f1720 0%, #121923 30%, #edf2f7 30%, #edf2f7 100%);
}

.shell-mobile {
  grid-template-columns: 1fr;
  background: linear-gradient(180deg, #0f1720 0%, #121923 14%, #edf2f7 14%, #edf2f7 100%);
}

.sidebar {
  padding: 22px 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  background: rgba(8, 13, 20, 0.94);
  backdrop-filter: blur(14px);
  color: #f6f1e8;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 50px;
  height: 50px;
  border-radius: 15px;
  display: grid;
  place-items: center;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #111827;
  background: linear-gradient(135deg, #d3a449, #f0d78a);
}

.brand-title,
.brand-subtitle,
.user-label,
.user-name,
.eyebrow,
.page-title {
  margin: 0;
}

.brand-title {
  font-size: 1.08rem;
  font-weight: 700;
}

.brand-subtitle {
  color: rgba(246, 241, 232, 0.68);
  font-size: 0.82rem;
  margin-top: 3px;
}

.brand-subtitle-dark {
  color: rgba(23, 32, 43, 0.62);
}

.nav,
.drawer-nav {
  display: grid;
  gap: 8px;
}

.nav-item {
  border: 1px solid transparent;
  border-radius: 16px;
  padding: 12px 14px;
  text-align: left;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  cursor: pointer;
  transition: transform 0.2s ease, background 0.2s ease, border-color 0.2s ease;
}

.nav-item-dark {
  background: #f7fafc;
  color: #17202b;
}

.nav-item:disabled,
.mobile-nav-item:disabled {
  cursor: default;
  opacity: 0.88;
}

.nav-item:hover,
.nav-item.active {
  transform: translateX(4px);
  background: rgba(211, 164, 73, 0.12);
  border-color: rgba(211, 164, 73, 0.42);
}

.nav-item-dark:hover,
.nav-item-dark.active {
  background: rgba(20, 71, 166, 0.08);
  border-color: rgba(20, 71, 166, 0.2);
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
  color: rgba(246, 241, 232, 0.56);
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.nav-path-dark {
  color: #64748b;
}

.sidebar-footer,
.drawer-footer {
  margin-top: auto;
  display: grid;
  gap: 10px;
}

.user-card {
  padding: 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.user-card-dark {
  background: #f7fafc;
  border-color: rgba(15, 23, 32, 0.08);
}

.user-label {
  color: rgba(246, 241, 232, 0.56);
  font-size: 0.76rem;
}

.user-card-dark .user-label {
  color: #64748b;
}

.user-name {
  margin-top: 5px;
  font-size: 0.96rem;
  font-weight: 600;
}

.logout-button {
  width: 100%;
}

.content {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.topbar {
  padding: 20px 24px 12px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.topbar-mobile {
  padding: 14px 16px 10px;
  gap: 12px;
  flex-direction: column;
  align-items: stretch;
}

.topbar-main {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.menu-button {
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.14);
  display: grid;
  place-items: center;
  gap: 4px;
  padding: 0;
  cursor: pointer;
  flex: 0 0 auto;
}

.menu-button span {
  width: 18px;
  height: 2px;
  border-radius: 999px;
  background: #f8fafc;
  display: block;
}

.eyebrow {
  color: #875f1f;
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.page-title {
  color: #f8fafc;
  font-size: clamp(1.65rem, 1.9vw, 2.2rem);
  font-weight: 700;
}

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

.topbar-badge {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(15, 23, 32, 0.08);
  color: #3b4652;
  font-size: 0.82rem;
}

.badge-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #0f9d58;
  box-shadow: 0 0 0 6px rgba(15, 157, 88, 0.12);
}

.main {
  min-width: 0;
  padding: 0 16px 16px;
}

.drawer-shell {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 18px;
  color: #17202b;
}

.mobile-nav {
  position: sticky;
  bottom: 0;
  z-index: 12;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  padding: 10px 12px calc(10px + env(safe-area-inset-bottom, 0px));
  background: rgba(8, 13, 20, 0.94);
  backdrop-filter: blur(16px);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.mobile-nav-item {
  border: 1px solid transparent;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  color: #f6f1e8;
  padding: 10px 8px;
  display: grid;
  gap: 3px;
  justify-items: center;
  cursor: pointer;
}

.mobile-nav-item.active {
  background: rgba(211, 164, 73, 0.14);
  border-color: rgba(211, 164, 73, 0.35);
}

.mobile-nav-text {
  display: grid;
  gap: 1px;
  justify-items: center;
}

.mobile-nav-label {
  font-size: 0.76rem;
  font-weight: 600;
}

.mobile-nav-hint {
  font-size: 0.64rem;
  color: rgba(246, 241, 232, 0.56);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

@media (max-width: 1100px) {
  .topbar {
    flex-direction: column;
    align-items: stretch;
  }
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

  .main {
    padding: 0 12px 12px;
  }

  .mobile-nav-label {
    font-size: 0.72rem;
  }

  .mobile-nav-hint {
    display: none;
  }
}
</style>
