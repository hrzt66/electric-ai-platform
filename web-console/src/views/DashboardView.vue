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
  { label: '任务总数', value: platformStore.tasks.length, hint: '全链路作业记录' },
  { label: '历史资产', value: platformStore.history.length, hint: '已入库生成结果' },
  { label: '可用模型', value: platformStore.models.length, hint: '生成与评分模型' },
  { label: '最新任务状态', value: latestTask.value?.status ?? '暂无', hint: latestTask.value?.model_name ?? '等待调度' },
])

const hasDashboardData = computed(
  () => platformStore.tasks.length > 0 || platformStore.history.length > 0 || platformStore.models.length > 0,
)

async function loadDashboard() {
  // 三块数据并行加载，优先保证首页“整体有内容”而不是逐块闪烁渲染。
  dashboardLoading.value = !hasDashboardData.value
  dashboardError.value = ''

  try {
    await Promise.all([platformStore.fetchTasks(), platformStore.fetchHistory(), platformStore.fetchModels()])
  } catch (error) {
    dashboardError.value =
      platformStore.tasksLoadError ||
      platformStore.historyLoadError ||
      platformStore.modelsLoadError ||
      '平台概览加载失败，请检查网关、任务服务和模型服务。'
  } finally {
    dashboardLoading.value = false
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
        <div>
          <p class="hero-eyebrow">平台概览</p>
          <h2 class="hero-title">{{ authStore.displayName || authStore.userName || '当前会话' }}</h2>
          <p class="hero-text">
            旧项目中的生成、评分、历史和模型视图已经迁回当前微服务架构。
            这里聚合展示任务调度、模型可用性和资产沉淀情况，方便你快速判断平台是否处于可用状态。
          </p>
        </div>
        <div class="hero-actions">
          <router-link class="hero-link" to="/generate">进入生成工作台</router-link>
        </div>
      </section>

      <section class="summary-grid">
        <article v-for="card in summaryCards" :key="card.label" class="summary-card mobile-compact-card">
          <span>{{ card.label }}</span>
          <strong>{{ card.value }}</strong>
          <small>{{ card.hint }}</small>
        </article>
      </section>

      <section class="list-grid">
        <div class="panel mobile-compact-card">
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

        <div class="panel mobile-compact-card">
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
  background: #ffffff;
  box-shadow: var(--ea-shadow);
}

.hero,
.panel,
.summary-card {
  border-radius: 24px;
  background: #ffffff;
  box-shadow: var(--ea-shadow);
}

.hero {
  padding: 28px;
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-end;
  background:
    linear-gradient(135deg, rgba(19, 71, 168, 0.96), rgba(15, 50, 120, 0.92)),
    linear-gradient(90deg, #0f1720, #17202b);
  color: #f8fafc;
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
  color: rgba(248, 250, 252, 0.7);
}

.hero-title {
  margin-top: 8px;
  font-size: clamp(1.8rem, 2vw, 2.4rem);
}

.hero-text {
  margin-top: 12px;
  max-width: 760px;
  line-height: 1.7;
  color: rgba(248, 250, 252, 0.78);
}

.hero-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 156px;
  padding: 12px 18px;
  border-radius: 999px;
  background: #f0d78a;
  color: #17202b;
  font-weight: 700;
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
}

.summary-card span,
.summary-card small {
  color: var(--ea-text-muted);
}

.summary-card strong {
  color: var(--ea-text);
  font-size: 1.8rem;
}

.list-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.panel {
  padding: 22px;
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
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero {
    align-items: stretch;
  }

  .mobile-compact-card {
    padding: 12px;
    border-radius: var(--ea-mobile-card-radius);
    box-shadow: var(--ea-mobile-card-shadow);
  }

  .dashboard,
  .summary-grid,
  .list-grid,
  .task-list,
  .model-list {
    gap: 10px;
  }

  .hero-actions,
  .hero-link {
    width: 100%;
  }

  .panel-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
