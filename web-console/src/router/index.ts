import { createMemoryHistory, createRouter, createWebHistory, type RouterHistory } from 'vue-router'

import AppShell from '../components/AppShell.vue'
import { useAuthStore } from '../stores/auth'
import DashboardView from '../views/DashboardView.vue'
import GenerateView from '../views/GenerateView.vue'
import HistoryView from '../views/HistoryView.vue'
import LoginView from '../views/LoginView.vue'
import ModelCenterView from '../views/ModelCenterView.vue'
import TaskAuditView from '../views/TaskAuditView.vue'

export function createAppRouter(history: RouterHistory) {
  const router = createRouter({
    history,
    routes: [
      { path: '/', redirect: '/dashboard' },
      { path: '/login', component: LoginView, meta: { guestOnly: true } },
      {
        path: '/',
        component: AppShell,
        meta: { requiresAuth: true },
        children: [
          { path: 'dashboard', component: DashboardView },
          { path: 'generate', component: GenerateView },
          { path: 'history', component: HistoryView },
          { path: 'models', component: ModelCenterView },
          { path: 'tasks/audit', component: TaskAuditView },
          { path: 'tasks/audit/:id', component: TaskAuditView },
        ],
      },
    ],
  })

  router.beforeEach((to) => {
    const authStore = useAuthStore()
    authStore.hydrate()

    const isAuthenticated = authStore.isAuthenticated
    if (to.meta.requiresAuth && !isAuthenticated) {
      return {
        path: '/login',
        query: to.fullPath === '/login' ? undefined : { redirect: to.fullPath },
      }
    }

    if (to.meta.guestOnly && isAuthenticated) {
      const redirect = typeof to.query.redirect === 'string' ? to.query.redirect : '/dashboard'
      return redirect
    }

    return true
  })

  return router
}

const router = createAppRouter(typeof window !== 'undefined' ? createWebHistory() : createMemoryHistory())

export default router
