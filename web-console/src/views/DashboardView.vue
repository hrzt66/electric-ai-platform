<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { useAuthStore } from '../stores/auth'
import { usePlatformStore } from '../stores/platform'

const authStore = useAuthStore()
const platformStore = usePlatformStore()
const dashboardLoading = ref(false)
const dashboardError = ref('')

const latestTask = computed(() =>
  [...platformStore.tasks].sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0] ?? null,
)

// 首页摘要卡片全部从 store 聚合状态推导，避免再单独发一轮摘要接口。
const summaryCards = computed(() => [
  { label: '任务总数', value: platformStore.taskAuditTotal, hint: '数据库中的全部作业记录' },
  { label: '历史资产', value: platformStore.historyTotal, hint: '数据库中的全部入库结果' },
  { label: '可用模型', value: platformStore.models.length, hint: '生成与评分模型' },
  { label: '最新任务状态', value: latestTask.value?.status ?? '暂无', hint: latestTask.value?.model_name ?? '等待调度' },
])

const hasDashboardData = computed(
  () =>
    platformStore.taskAuditTotal > 0 ||
    platformStore.historyTotal > 0 ||
    platformStore.tasks.length > 0 ||
    platformStore.history.length > 0 ||
    platformStore.models.length > 0,
)

async function loadDashboard() {
  // 三块数据并行加载，优先保证首页“整体有内容”而不是逐块闪烁渲染。
  dashboardLoading.value = !hasDashboardData.value
  dashboardError.value = ''

  try {
    await Promise.all([
      platformStore.fetchTasks(),
      platformStore.fetchHistory(),
      platformStore.fetchHistoryPage({ page: 1, page_size: 10 }),
      platformStore.fetchTaskAuditPage({ page: 1, page_size: 10 }),
      platformStore.fetchModels(),
    ])
  } catch (error) {
    dashboardError.value =
      platformStore.tasksLoadError ||
      platformStore.historyLoadError ||
      platformStore.modelsLoadError ||
      '平台概览加载失败，请检查网关、任务服务和模型服务。'
  } finally {
    dashboardLoading.value = false
  }

  try {
    await platformStore.fetchMonitorOverview?.()
  } catch {
    // 监控面板加载失败时，不阻塞首页主数据展示。
  }
}

onMounted(() => {
  void loadDashboard()
})
</script>

<template>
  <div class="dashboard">
    <el-alert v-if="dashboardError" :closable="false" type="warning" show-icon :title="dashboardError" />

    <el-skeleton v-if="dashboardLoading" class="page-skeleton" animated :rows="10" />

    <template v-else>
      <section class="hero">
        <div class="hero-copy">
          <p class="hero-eyebrow">Platform Overview</p>
          <h2 class="hero-title">统一平台总览</h2>
          <p class="hero-text">
            面向 {{ authStore.displayName || authStore.userName || '当前会话' }} 的生成式电力 AI 平台入口，统一查看生成、评分与资产沉淀的实时状态。
          </p>
          <p class="hero-caption">聚焦任务吞吐、模型供给与最近执行动态，进入工作台即可继续联动作业。</p>
        </div>
        <router-link class="hero-link" to="/generate" title='href="/generate"'>进入生成工作台</router-link>
      </section>

      <section class="summary-grid">
        <article v-for="card in summaryCards" :key="card.label" class="summary-card">
          <span>{{ card.label }}</span>
          <strong>{{ card.value }}</strong>
          <small>{{ card.hint }}</small>
        </article>
      </section>

      <section class="list-grid">
        <div class="panel">
          <div class="panel-header">
            <h3>最近任务</h3>
            <router-link to="/tasks/audit">查看审计</router-link>
          </div>
          <div v-if="platformStore.tasks.length" class="task-list">
            <article v-for="task in platformStore.tasks.slice(0, 6)" :key="task.id" class="task-item">
              <div>
                <strong>#{{ task.id }} {{ task.model_name }}</strong>
                <p>{{ task.prompt }}</p>
              </div>
              <el-tag :type="task.status === 'completed' ? 'success' : task.status === 'failed' ? 'danger' : 'warning'">
                {{ task.status }}
              </el-tag>
            </article>
          </div>
          <el-empty v-else description="当前还没有任务记录，先去生成工作台提交一条任务。" />
        </div>

        <div class="panel">
          <div class="panel-header">
            <h3>可用模型</h3>
            <router-link to="/models">进入模型中心</router-link>
          </div>
          <div v-if="platformStore.models.length" class="model-list">
            <article v-for="model in platformStore.models.slice(0, 4)" :key="model.id" class="model-item">
              <strong>{{ model.display_name || model.model_name }}</strong>
              <p>{{ model.description || model.local_path }}</p>
              <el-tag :type="model.status === 'available' ? 'success' : model.status === 'experimental' ? 'warning' : 'info'">
                {{ model.status }}
              </el-tag>
            </article>
          </div>
          <el-empty v-else description="模型列表尚未加载，请检查网关和模型服务。" />
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.dashboard {
  display: grid;
  gap: 20px;
}

.page-skeleton {
  border-radius: 24px;
  padding: 24px;
  background: var(--ea-surface);
  border: 1px solid var(--ea-border);
  box-shadow: var(--ea-shadow);
}

.hero,
.panel,
.summary-card {
  border-radius: 24px;
  border: 1px solid var(--ea-border);
  box-shadow: var(--ea-shadow);
}

.hero {
  padding: 28px;
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-end;
  background:
    radial-gradient(circle at top right, rgba(29, 78, 216, 0.08), transparent 32%),
    linear-gradient(135deg, #ffffff, #f8fafc 58%, #f1f5f9);
  color: var(--ea-text);
  position: relative;
  overflow: hidden;
}

.hero::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(120deg, rgba(29, 78, 216, 0.03), transparent 36%),
    repeating-linear-gradient(
      90deg,
      rgba(148, 163, 184, 0.03) 0,
      rgba(148, 163, 184, 0.03) 1px,
      transparent 1px,
      transparent 72px
    );
  pointer-events: none;
}

.hero-copy,
.hero-link {
  position: relative;
  z-index: 1;
}

.hero-eyebrow,
.hero-title,
.hero-text {
  margin: 0;
}

.hero-eyebrow {
  font-size: 0.82rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ea-primary-strong);
}

.hero-title {
  margin-top: 8px;
  font-size: clamp(1.8rem, 2vw, 2.4rem);
}

.hero-text {
  margin-top: 12px;
  max-width: 760px;
  line-height: 1.7;
  color: var(--ea-text-muted);
}

.hero-caption {
  margin: 12px 0 0;
  color: var(--ea-text-muted);
  font-size: 0.95rem;
  line-height: 1.6;
}

.hero-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 156px;
  padding: 12px 18px;
  border-radius: 999px;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: #ffffff;
  font-weight: 700;
  border: 1px solid rgba(29, 78, 216, 0.16);
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.18);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.summary-card {
  padding: 18px 20px;
  display: grid;
  gap: 8px;
  background: var(--ea-surface);
}

.summary-card span,
.summary-card small {
  color: var(--ea-text-muted);
}

.summary-card strong {
  color: var(--ea-text);
  font-size: 1.8rem;
  letter-spacing: 0.02em;
}

.list-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.panel {
  padding: 22px;
  background: var(--ea-surface);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  margin-bottom: 14px;
}

.panel-header h3,
.task-item p,
.model-item p {
  margin: 0;
}

.panel-header a {
  color: var(--ea-primary);
}

.panel-header h3,
.task-item strong,
.model-item strong {
  color: var(--ea-text);
}

.task-list,
.model-list {
  display: grid;
  gap: 12px;
}

.task-item,
.model-item {
  display: grid;
  gap: 8px;
  padding: 14px 16px;
  border-radius: 18px;
  background: var(--ea-surface-alt);
  border: 1px solid var(--ea-border);
}

.task-item p,
.model-item p {
  color: var(--ea-text-muted);
}

@media (max-width: 1100px) {
  .summary-grid,
  .list-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .hero,
  .summary-grid,
  .list-grid {
    display: grid;
    grid-template-columns: 1fr;
  }
}
</style>
