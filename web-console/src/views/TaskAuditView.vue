<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { usePlatformStore } from '../stores/platform'
import { resolveAuditTaskId } from './task-audit-utils'

const route = useRoute()
const platformStore = usePlatformStore()
const auditPageLoading = ref(false)
const auditPageError = ref('')
const bootstrappingAudit = ref(false)

const routeTaskId = computed(() => {
  const value = typeof route.params.id === 'string' ? Number(route.params.id) : NaN
  return Number.isFinite(value) && value > 0 ? value : null
})

// 审计页既支持显式路由参数，也支持从当前任务、任务列表或历史记录里自动推导目标任务。
const taskId = computed(() =>
  resolveAuditTaskId({
    routeTaskId: routeTaskId.value,
    currentTaskId: platformStore.currentTaskId,
    tasks: platformStore.tasks,
    history: platformStore.history,
  }),
)

const linkedAssets = computed(() => {
  if (!taskId.value) {
    return []
  }

  return platformStore.history.filter((item) => item.job_id === taskId.value)
})

async function bootstrapAuditContext() {
  // 页面首次进入且还没有明确 taskId 时，先把任务与历史上下文拉齐。
  if (bootstrappingAudit.value) {
    return
  }

  bootstrappingAudit.value = true
  auditPageLoading.value = true
  auditPageError.value = ''

  try {
    await Promise.all([platformStore.fetchTasks(), platformStore.fetchHistory()])
  } catch (error) {
    auditPageError.value = platformStore.tasksLoadError || platformStore.historyLoadError || '审计页初始化失败，请检查任务与资产链路。'
  } finally {
    bootstrappingAudit.value = false
    if (!taskId.value) {
      auditPageLoading.value = false
    }
  }
}

async function loadTaskAuditPage(targetTaskId: number) {
  // 如果当前任务详情或关联资产尚不完整，就补拉一次，保证页面中央面板能完整展示。
  auditPageLoading.value =
    !platformStore.currentTask ||
    platformStore.currentTask.id !== targetTaskId ||
    platformStore.currentTaskAudit.length === 0 ||
    linkedAssets.value.length === 0
  auditPageError.value = ''

  try {
    await platformStore.refreshTask(targetTaskId)
    if (linkedAssets.value.length === 0) {
      await platformStore.fetchHistory()
    }
  } catch (error) {
    auditPageError.value =
      platformStore.taskLoadError || platformStore.historyLoadError || `任务 #${targetTaskId} 加载失败，请检查审计链路。`
  } finally {
    auditPageLoading.value = false
  }
}

watch(
  taskId,
  (nextTaskId) => {
    if (nextTaskId) {
      void loadTaskAuditPage(nextTaskId)
      return
    }

    void bootstrapAuditContext()
  },
  { immediate: true },
)
</script>

<template>
  <div class="audit-page">
    <el-alert v-if="auditPageError" :closable="false" type="warning" show-icon :title="auditPageError" />

    <el-skeleton v-if="auditPageLoading" class="page-skeleton" animated :rows="8" />

    <el-empty
      v-else-if="!taskId"
      description="当前还没有可查看的任务审计，先去生成工作台提交一条真实任务。"
    />

    <template v-else>
      <section class="summary-card">
        <div>
          <p class="summary-eyebrow">任务审计</p>
          <h2 class="summary-title">任务 #{{ taskId || '--' }}</h2>
        </div>
        <el-tag v-if="platformStore.currentTask">{{ platformStore.currentTask.status }}</el-tag>
      </section>

      <section class="content-grid">
        <div class="panel">
          <div class="panel-header">
            <h3>时间线</h3>
          </div>
          <el-empty v-if="platformStore.currentTaskAudit.length === 0" description="当前没有可展示的审计事件。" />
          <el-timeline v-else>
            <el-timeline-item v-for="event in platformStore.currentTaskAudit" :key="event.id" :timestamp="event.created_at" placement="top">
              <strong>{{ event.event_type }}</strong>
              <p class="timeline-body">{{ event.payload_json || event.message || '无附加信息' }}</p>
            </el-timeline-item>
          </el-timeline>
        </div>

        <div class="panel">
          <div class="panel-header">
            <h3>关联资产</h3>
          </div>
          <el-empty v-if="linkedAssets.length === 0" description="该任务还没有可展示的关联资产，或历史数据尚未同步。" />
          <div v-else class="asset-list">
            <article v-for="asset in linkedAssets" :key="asset.id" class="asset-item">
              <strong>{{ asset.image_name }}</strong>
              <p>{{ asset.model_name }} / 总分 {{ asset.total_score.toFixed(2) }}</p>
            </article>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.audit-page {
  display: grid;
  gap: 20px;
}

.page-skeleton {
  border-radius: 24px;
  padding: 24px;
  background: #ffffff;
  box-shadow: var(--ea-shadow);
}

.summary-card,
.panel {
  padding: 22px;
  border-radius: 24px;
  background: #ffffff;
  box-shadow: var(--ea-shadow);
}

.summary-card {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.summary-eyebrow,
.summary-title,
.timeline-body,
.asset-item p {
  margin: 0;
}

.summary-eyebrow {
  color: #8a5c18;
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.summary-title {
  margin-top: 6px;
  color: #17202b;
  font-size: 1.5rem;
}

.content-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.panel-header {
  margin-bottom: 14px;
}

.panel-header h3 {
  margin: 0;
}

.timeline-body,
.asset-item p {
  color: #53606f;
}

.asset-list {
  display: grid;
  gap: 12px;
}

.asset-item {
  padding: 14px 16px;
  border-radius: 18px;
  background: #f8fafc;
}

@media (max-width: 920px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>
