<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import AuditTimeline from '../components/audit/AuditTimeline.vue'
import { usePlatformStore } from '../stores/platform'
import type { GenerateTask } from '../types/platform'
import { localizeTaskAuditStatus } from './task-audit-status'
import { resolveAuditTaskId } from './task-audit-utils'

const DEFAULT_PAGE_SIZE = 10

const route = useRoute()
const platformStore = usePlatformStore()

const initialLoading = ref(true)
const listError = ref('')
const detailLoading = ref(false)
const detailError = ref('')
const detailDialogVisible = ref(false)
const selectedTaskId = ref<number | null>(null)
const hasMounted = ref(false)

let pageQueueRunning = false
let pendingPageRequest: {
  page: number
  pageSize: number
  preferredTaskId?: number | null
  selectionMode: 'preferred-or-first' | 'first'
} | null = null

let detailQueueRunning = false
let pendingDetailTaskId: number | null | undefined

const explicitRouteTaskId = computed(() =>
  resolveAuditTaskId({
    routeTaskId: typeof route.params.id === 'string' ? Number(route.params.id) : null,
  }),
)

const selectedTask = computed(() => {
  if (platformStore.currentTask?.id === selectedTaskId.value) {
    return platformStore.currentTask
  }

  return platformStore.taskAuditPageItems.find((task) => task.id === selectedTaskId.value) ?? null
})

const taskSummaryCards = computed(() => [
  {
    label: '任务总数',
    value: String(platformStore.taskAuditTotal),
    hint: '全部生成任务按更新时间倒序分页展示',
  },
  {
    label: '当前分页',
    value: `${platformStore.taskAuditPage || 1} / ${platformStore.taskAuditTotalPages || 1}`,
    hint: `本页已载入 ${platformStore.taskAuditPageItems.length} 条任务`,
  },
  {
    label: '当前选中',
    value: selectedTaskId.value ? `#${selectedTaskId.value}` : '--',
    hint: selectedTask.value?.stage || '点击任务弹出完整时间线',
  },
])

const linkedAssets = computed(() => {
  if (!selectedTaskId.value) {
    return []
  }

  return platformStore.history.filter((item) => item.job_id === selectedTaskId.value)
})

const hasAnyTask = computed(() => platformStore.taskAuditTotal > 0 || platformStore.taskAuditPageItems.length > 0)

const timelineEvents = computed(() => (platformStore.currentTask?.id === selectedTaskId.value ? platformStore.currentTaskAudit : []))

const selectedTaskScoringModel = computed(
  () => selectedTask.value?.scoring_model_name?.trim() || '未配置评分模型，沿用默认评分链路',
)

const selectedTaskErrorMessage = computed(() => selectedTask.value?.error_message?.trim() || '暂无异常信息')

const sortedAllTasks = computed(() =>
  [...platformStore.tasks].sort((left, right) => {
    const rightTime = Date.parse(right.updated_at || right.created_at || '')
    const leftTime = Date.parse(left.updated_at || left.created_at || '')

    if (Number.isFinite(rightTime) && Number.isFinite(leftTime) && rightTime !== leftTime) {
      return rightTime - leftTime
    }

    if (Number.isFinite(rightTime) && !Number.isFinite(leftTime)) {
      return -1
    }

    if (!Number.isFinite(rightTime) && Number.isFinite(leftTime)) {
      return 1
    }

    return right.id - left.id
  }),
)

function formatDateTime(value?: string) {
  if (!value) {
    return '--'
  }

  const timestamp = Date.parse(value)
  if (Number.isNaN(timestamp)) {
    return value
  }

  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(timestamp)
}

function resolveStatusTagType(status?: string) {
  if (status === 'completed' || status === 'scored') {
    return 'success'
  }

  if (status === 'failed') {
    return 'danger'
  }

  if (status === 'queued' || status === 'pending') {
    return 'info'
  }

  return 'warning'
}

function findTaskPage(taskId: number, pageSize: number) {
  const taskIndex = sortedAllTasks.value.findIndex((task) => task.id === taskId)

  if (taskIndex < 0) {
    return null
  }

  return Math.floor(taskIndex / pageSize) + 1
}

async function loadTaskDetail(taskId: number) {
  detailError.value = ''

  try {
    await platformStore.refreshTask(taskId)

    if (linkedAssets.value.length === 0) {
      await platformStore.fetchHistory()
    }
  } catch {
    detailError.value =
      platformStore.taskLoadError || platformStore.historyLoadError || `任务 #${taskId} 审计详情加载失败，请检查任务与资产链路。`
  }
}

async function queueTaskSelection(taskId: number | null) {
  selectedTaskId.value = taskId
  pendingDetailTaskId = taskId

  if (detailQueueRunning) {
    return
  }

  detailQueueRunning = true

  while (pendingDetailTaskId !== undefined) {
    const nextTaskId = pendingDetailTaskId
    pendingDetailTaskId = undefined
    detailLoading.value = Boolean(nextTaskId)

    if (!nextTaskId) {
      detailError.value = ''
      continue
    }

    await loadTaskDetail(nextTaskId)
  }

  detailLoading.value = false
  detailQueueRunning = false
}

async function loadAuditPage(options: {
  page: number
  pageSize: number
  preferredTaskId?: number | null
  selectionMode: 'preferred-or-first' | 'first'
}) {
  listError.value = ''

  try {
    await platformStore.fetchTaskAuditPage({
      page: options.page,
      page_size: options.pageSize,
    })

    let pageItems = platformStore.taskAuditPageItems

    if (options.preferredTaskId && !pageItems.some((task) => task.id === options.preferredTaskId)) {
      const preferredTaskPage = findTaskPage(options.preferredTaskId, options.pageSize)

      if (preferredTaskPage && preferredTaskPage !== options.page) {
        await platformStore.fetchTaskAuditPage({
          page: preferredTaskPage,
          page_size: options.pageSize,
        })
        pageItems = platformStore.taskAuditPageItems
      }
    }

    if (pageItems.length === 0) {
      await queueTaskSelection(null)
      return
    }

    const nextSelectedTaskId =
      options.preferredTaskId && pageItems.some((task) => task.id === options.preferredTaskId)
        ? options.preferredTaskId
        : options.selectionMode === 'first'
          ? pageItems[0].id
          : pageItems[0].id

    await queueTaskSelection(nextSelectedTaskId)
  } catch {
    listError.value = platformStore.taskAuditPageLoadError || '任务审计分页加载失败，请检查任务服务链路。'
    await queueTaskSelection(null)
  } finally {
    initialLoading.value = false
  }
}

async function queueAuditPageLoad(options: {
  page: number
  pageSize: number
  preferredTaskId?: number | null
  selectionMode: 'preferred-or-first' | 'first'
}) {
  pendingPageRequest = options

  if (pageQueueRunning) {
    return
  }

  pageQueueRunning = true

  while (pendingPageRequest) {
    const nextRequest = pendingPageRequest
    pendingPageRequest = null
    await loadAuditPage(nextRequest)
  }

  pageQueueRunning = false
}

function handleTaskSelect(task: GenerateTask) {
  detailDialogVisible.value = true
  void queueTaskSelection(task.id)
}

function handlePageChange(page: number) {
  void queueAuditPageLoad({
    page,
    pageSize: platformStore.taskAuditPageSize || DEFAULT_PAGE_SIZE,
    selectionMode: 'first',
  })
}

function handlePageSizeChange(pageSize: number) {
  void queueAuditPageLoad({
    page: 1,
    pageSize,
    selectionMode: 'first',
  })
}

onMounted(() => {
  hasMounted.value = true

  void queueAuditPageLoad({
    page: 1,
    pageSize: platformStore.taskAuditPageSize || DEFAULT_PAGE_SIZE,
    preferredTaskId: explicitRouteTaskId.value,
    selectionMode: 'preferred-or-first',
  })
})

watch(explicitRouteTaskId, (nextTaskId, previousTaskId) => {
  if (!hasMounted.value || nextTaskId === previousTaskId || !nextTaskId) {
    return
  }

  void queueAuditPageLoad({
    page: platformStore.taskAuditPage || 1,
    pageSize: platformStore.taskAuditPageSize || DEFAULT_PAGE_SIZE,
    preferredTaskId: nextTaskId,
    selectionMode: 'preferred-or-first',
  })
})
</script>

<template>
  <div class="audit-page">
    <el-alert v-if="listError" :closable="false" type="warning" show-icon :title="listError" />

    <el-skeleton v-if="initialLoading" class="page-skeleton" animated :rows="10" />

    <template v-else>
      <section class="hero">
        <div class="hero-copy">
          <p class="hero-eyebrow">Task Audit Hub</p>
          <h2 class="hero-title">任务审计中心</h2>
          <p class="hero-text">
            延续历史中心的浏览节奏，先按页查看全部任务，再通过弹窗查看单个任务的完整审计时间线与结果沉淀。
          </p>
        </div>

        <div class="hero-metrics">
          <article v-for="card in taskSummaryCards" :key="card.label" class="hero-metric">
            <span>{{ card.label }}</span>
            <strong>{{ card.value }}</strong>
            <small>{{ card.hint }}</small>
          </article>
        </div>
      </section>

      <section class="panel list-panel">
        <div class="panel-header">
          <div>
            <p class="panel-eyebrow">分页任务列表</p>
            <h3>全部审计任务</h3>
          </div>
          <el-tag type="info">当前页 {{ platformStore.taskAuditPageItems.length }} 条</el-tag>
        </div>

        <el-empty
          v-if="!platformStore.loadingTaskAuditPage && !hasAnyTask"
          description="当前还没有可查看的任务审计，先去生成工作台提交一条真实任务。"
        />

        <template v-else>
          <div v-loading="platformStore.loadingTaskAuditPage" class="task-list">
            <button
              v-for="task in platformStore.taskAuditPageItems"
              :key="task.id"
              type="button"
              class="task-row"
              :class="{ selected: task.id === selectedTaskId }"
              @click="handleTaskSelect(task)"
            >
              <div class="task-info-grid">
                <div class="task-main">
                  <div class="task-primary">
                    <strong class="task-id">任务 #{{ task.id }}</strong>
                    <el-tag size="small" :type="resolveStatusTagType(task.status)">{{ localizeTaskAuditStatus(task.status) }}</el-tag>
                    <span class="task-stage">{{ task.stage || '未知阶段' }}</span>
                  </div>
                  <p class="task-prompt">{{ task.prompt || '暂无提示词摘要' }}</p>
                </div>

                <div class="task-cell">
                  <span class="task-label">生成模型</span>
                  <strong>{{ task.model_name || '--' }}</strong>
                </div>

                <div class="task-cell">
                  <span class="task-label">评分模型</span>
                  <strong>{{ task.scoring_model_name?.trim() || '默认评分链路' }}</strong>
                </div>

                <div class="task-cell">
                  <span class="task-label">创建时间</span>
                  <strong>{{ formatDateTime(task.created_at) }}</strong>
                </div>

                <div class="task-cell">
                  <span class="task-label">更新时间</span>
                  <strong>{{ formatDateTime(task.updated_at) }}</strong>
                </div>
              </div>

              <div class="task-action">
                <span>查看时间线</span>
              </div>
            </button>
          </div>

          <div v-if="hasAnyTask" class="pagination-card">
            <el-pagination
              background
              layout="total, sizes, prev, pager, next"
              :total="platformStore.taskAuditTotal"
              :current-page="platformStore.taskAuditPage"
              :page-size="platformStore.taskAuditPageSize"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="handlePageChange"
              @size-change="handlePageSizeChange"
            />
          </div>
        </template>
      </section>

      <el-alert v-if="detailError" :closable="false" type="warning" show-icon :title="detailError" />
    </template>

    <el-dialog
      v-model="detailDialogVisible"
      class="audit-detail-dialog"
      width="min(1080px, calc(100vw - 32px))"
      destroy-on-close
      append-to-body
    >
      <template #header>
        <div class="dialog-header" v-if="selectedTask">
          <div>
            <p class="panel-eyebrow">完整时间线</p>
            <h3>任务 #{{ selectedTask.id }} 审计轨迹</h3>
          </div>
          <el-tag :type="resolveStatusTagType(selectedTask.status)">{{ localizeTaskAuditStatus(selectedTask.status) }}</el-tag>
        </div>
      </template>

      <div v-if="selectedTask" class="dialog-content" v-loading="detailLoading">
        <section class="dialog-panel timeline-panel">
          <AuditTimeline :events="timelineEvents" empty-description="当前没有可展示的审计事件。" />
        </section>

        <section class="dialog-panel asset-panel">
          <div class="panel-header">
            <div>
              <p class="panel-eyebrow">关联资产</p>
              <h3>任务结果沉淀</h3>
            </div>
            <el-tag type="info">{{ linkedAssets.length }} 项</el-tag>
          </div>

          <div class="dialog-meta">
            <span>生成模型：{{ selectedTask.model_name || '--' }}</span>
            <span>评分模型：{{ selectedTaskScoringModel }}</span>
            <span>更新时间：{{ formatDateTime(selectedTask.updated_at) }}</span>
          </div>

          <el-alert
            v-if="selectedTask.error_message"
            type="warning"
            show-icon
            :closable="false"
            :title="selectedTaskErrorMessage"
          />

          <el-empty v-if="linkedAssets.length === 0" description="该任务还没有可展示的关联资产，或历史数据尚未同步。" />

          <div v-else class="asset-list">
            <article v-for="asset in linkedAssets" :key="asset.id" class="asset-item">
              <div class="asset-title">
                <strong>{{ asset.image_name }}</strong>
                <el-tag size="small" :type="resolveStatusTagType(asset.status)">{{ localizeTaskAuditStatus(asset.status) }}</el-tag>
              </div>
              <p>{{ asset.model_name }} / 总分 {{ asset.total_score.toFixed(2) }}</p>
              <small>{{ formatDateTime(asset.created_at) }}</small>
            </article>
          </div>
        </section>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.audit-page {
  display: grid;
  gap: 20px;
}

.hero,
.panel,
.page-skeleton {
  border-radius: 24px;
  border: 1px solid var(--ea-border);
}

.hero {
  position: relative;
  overflow: hidden;
  display: grid;
  gap: 20px;
  padding: 24px;
  background:
    radial-gradient(circle at top right, rgba(29, 78, 216, 0.08), transparent 32%),
    linear-gradient(135deg, #ffffff, #f8fafc 58%, #f1f5f9);
  color: var(--ea-text);
  box-shadow: var(--ea-shadow);
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
.hero-metrics,
.asset-list {
  display: grid;
}

.hero-copy,
.hero-metrics {
  position: relative;
  z-index: 1;
}

.hero-copy {
  gap: 8px;
}

.hero-eyebrow,
.hero-title,
.hero-text,
.panel-eyebrow,
.panel-header h3,
.task-label,
.task-prompt,
.asset-item p,
.asset-item small {
  margin: 0;
}

.hero-eyebrow,
.panel-eyebrow {
  font-size: 0.82rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.hero-eyebrow {
  color: var(--ea-primary-strong);
}

.hero-title {
  font-size: clamp(1.7rem, 2vw, 2.2rem);
}

.hero-text {
  max-width: 760px;
  line-height: 1.7;
  color: var(--ea-text-muted);
}

.hero-metrics {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.hero-metric {
  display: grid;
  gap: 8px;
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.96);
  border: 1px solid var(--ea-border);
}

.hero-metric span,
.dialog-meta span {
  color: var(--ea-text-muted);
  font-size: 0.85rem;
}

.hero-metric strong {
  font-size: 1.45rem;
  color: var(--ea-text);
}

.hero-metric small {
  color: var(--ea-text-muted);
  line-height: 1.5;
}

.panel,
.page-skeleton {
  padding: 22px;
  background: #ffffff;
  box-shadow: var(--ea-shadow);
}

.page-skeleton {
  min-height: 280px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.panel-eyebrow {
  color: var(--ea-primary-strong);
}

.panel-header h3 {
  margin-top: 6px;
  color: var(--ea-text);
}

.task-list {
  display: grid;
  gap: 12px;
  min-height: 140px;
}

.task-row {
  display: flex;
  gap: 18px;
  justify-content: space-between;
  width: 100%;
  padding: 18px 20px;
  align-items: center;
  border: 1px solid var(--ea-border);
  border-radius: 20px;
  background: var(--ea-surface);
  text-align: left;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.task-row:hover,
.task-row.selected {
  transform: translateY(-1px);
  border-color: rgba(29, 78, 216, 0.24);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.1);
}

.task-row.selected {
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.98), rgba(255, 255, 255, 0.98)), #ffffff;
}

.task-info-grid {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) repeat(3, minmax(140px, 0.8fr));
  gap: 14px;
  align-items: center;
}

.task-main {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.task-primary {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.task-id {
  color: var(--ea-text);
  font-size: 1rem;
}

.task-stage {
  color: var(--ea-text-muted);
  font-size: 0.86rem;
}

.task-prompt {
  color: var(--ea-text-muted);
  font-size: 0.88rem;
  line-height: 1.6;
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.task-cell,
.task-action {
  display: grid;
  gap: 8px;
  align-content: start;
}

.task-label {
  font-size: 0.8rem;
  color: var(--ea-text-muted);
}

.task-cell strong,
.task-action span,
.asset-item strong {
  color: var(--ea-text);
}

.task-cell strong,
.task-cell small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-cell small,
.asset-item p,
.asset-item small {
  color: var(--ea-text-muted);
  line-height: 1.55;
}

.task-action {
  flex: 0 0 auto;
  justify-items: end;
  align-items: center;
  justify-self: end;
}

.task-action span {
  font-weight: 600;
  white-space: nowrap;
}

.pagination-card {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}

.pagination-card :deep(.el-pagination) {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.asset-list {
  gap: 16px;
}

.asset-item {
  padding: 16px;
  border-radius: 18px;
  background: var(--ea-surface-alt);
  border: 1px solid var(--ea-border);
}

.asset-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 8px;
}

.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-right: 28px;
}

.dialog-header h3 {
  margin: 6px 0 0;
  color: var(--ea-text);
}

.dialog-content {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.95fr);
  gap: 20px;
  min-height: 320px;
}

.dialog-panel {
  padding: 4px 0;
}

.dialog-meta {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
  color: var(--ea-text-muted);
}

:deep(.audit-detail-dialog .el-dialog) {
  border-radius: 28px;
}

:deep(.audit-detail-dialog .el-dialog__body) {
  padding-top: 6px;
}

.pagination-card :deep(.el-pagination .btn-next),
.pagination-card :deep(.el-pagination .btn-prev),
.pagination-card :deep(.el-pagination .el-pager li),
.pagination-card :deep(.el-pagination .el-pagination__sizes .el-select__wrapper) {
  background: #f8fafc;
  border-color: var(--ea-border);
  color: var(--ea-text);
}

@media (max-width: 1180px) {
  .hero-metrics {
    grid-template-columns: 1fr;
  }

  .task-info-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .task-row {
    align-items: flex-end;
  }

  .dialog-content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .panel,
  .hero,
  .page-skeleton {
    padding: 18px;
  }

  .task-row {
    flex-direction: column;
    align-items: stretch;
  }

  .task-info-grid,
  .dialog-content {
    grid-template-columns: 1fr;
  }

  .task-action {
    justify-items: start;
    justify-self: start;
  }

  .pagination-card {
    justify-content: center;
  }
}
</style>
