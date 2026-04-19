import { defineStore } from 'pinia'

import {
  createGenerateTask,
  getAssetDetail,
  getTask,
  listAssetHistory,
  listAssetHistoryPage,
  listModels,
  listTaskAuditEvents,
  listTasks,
} from '../api/platform'
import { localizeModelRecords } from '../model-copy'
import type {
  AssetDetail,
  AssetHistoryPage,
  AssetHistoryPageQuery,
  AssetHistoryItem,
  AuditEvent,
  GenerateTask,
  GenerateTaskRequest,
  ModelRecord,
} from '../types/platform'

const CACHE_TTL_MS = 5_000

function isCacheFresh(timestamp: number, ttl = CACHE_TTL_MS) {
  // 判断缓存是否仍在有效期内，避免页面反复切换时重复打网关。
  return timestamp > 0 && Date.now() - timestamp < ttl
}

function ensureArray<T>(value: T[] | null | undefined): T[] {
  // 后端偶发返回 null 时，在 store 层兜底为 []，避免页面计算属性直接崩掉。
  return Array.isArray(value) ? value : []
}

function ensureHistoryPage(value: AssetHistoryPage | null | undefined): AssetHistoryPage {
  return {
    items: ensureArray(value?.items),
    page: typeof value?.page === 'number' && value.page > 0 ? value.page : 1,
    page_size: typeof value?.page_size === 'number' && value.page_size > 0 ? value.page_size : 10,
    total: typeof value?.total === 'number' && value.total >= 0 ? value.total : 0,
    total_pages: typeof value?.total_pages === 'number' && value.total_pages >= 0 ? value.total_pages : 0,
  }
}

function dedupeCurrentTaskAssets(items: AssetHistoryItem[]) {
  const seen = new Set<string>()
  return items.filter((item) => {
    const key = `${item.job_id}:${item.image_name || item.file_path}`
    if (seen.has(key)) {
      return false
    }
    seen.add(key)
    return true
  })
}

function extractErrorMessage(error: unknown, fallback: string) {
  // 优先读取后端 envelope.message，其次退回 Error.message，再退回兜底文案。
  if (typeof error === 'object' && error !== null) {
    const responseMessage = (error as { response?: { data?: { message?: unknown } } }).response?.data?.message
    if (typeof responseMessage === 'string' && responseMessage.trim()) {
      return responseMessage
    }

    const message = (error as { message?: unknown }).message
    if (typeof message === 'string' && message.trim()) {
      return message
    }
  }

  return fallback
}

type PlatformState = {
  models: ModelRecord[]
  tasks: GenerateTask[]
  history: AssetHistoryItem[]
  historyPageItems: AssetHistoryItem[]
  historyPage: number
  historyPageSize: number
  historyTotal: number
  historyTotalPages: number
  currentTask: GenerateTask | null
  currentAssets: AssetHistoryItem[]
  currentTaskAudit: AuditEvent[]
  selectedAssetDetail: AssetDetail | null
  submitting: boolean
  loadingTasks: boolean
  loadingHistory: boolean
  loadingHistoryPage: boolean
  loadingModels: boolean
  loadingTask: boolean
  tasksLoadError: string | null
  historyLoadError: string | null
  historyPageLoadError: string | null
  modelsLoadError: string | null
  taskLoadError: string | null
  tasksLoadedAt: number
  historyLoadedAt: number
  modelsLoadedAt: number
  tasksRequest: Promise<GenerateTask[]> | null
  historyRequest: Promise<AssetHistoryItem[]> | null
  modelsRequest: Promise<ModelRecord[]> | null
  taskRequests: Record<number, Promise<GenerateTask>>
  historyPageRequestToken: number
}

export const usePlatformStore = defineStore('platform', {
  state: (): PlatformState => ({
    models: [],
    tasks: [],
    history: [],
    historyPageItems: [],
    historyPage: 1,
    historyPageSize: 10,
    historyTotal: 0,
    historyTotalPages: 0,
    currentTask: null,
    currentAssets: [],
    currentTaskAudit: [],
    selectedAssetDetail: null,
    submitting: false,
    loadingTasks: false,
    loadingHistory: false,
    loadingHistoryPage: false,
    loadingModels: false,
    loadingTask: false,
    tasksLoadError: null,
    historyLoadError: null,
    historyPageLoadError: null,
    modelsLoadError: null,
    taskLoadError: null,
    tasksLoadedAt: 0,
    historyLoadedAt: 0,
    modelsLoadedAt: 0,
    tasksRequest: null,
    historyRequest: null,
    modelsRequest: null,
    taskRequests: {},
    historyPageRequestToken: 0,
  }),
  getters: {
    currentTaskId(state) {
      return state.currentTask?.id ?? null
    },
  },
  actions: {
    async submitGenerateJob(payload: GenerateTaskRequest) {
      // 提交任务后立即把 currentTask 切到新任务，保证工作台第一时间进入轮询状态。
      this.submitting = true
      try {
        const task = await createGenerateTask(payload)
        this.currentTask = task
        this.tasks = [task, ...this.tasks.filter((item) => item.id !== task.id)]
        this.tasksLoadedAt = Date.now()
        this.tasksLoadError = null
        this.currentAssets = []
        this.currentTaskAudit = []
        this.selectedAssetDetail = null
        this.taskLoadError = null
        return task
      } finally {
        this.submitting = false
      }
    },

    async fetchTasks(options?: { force?: boolean }) {
      const force = options?.force ?? false

      if (!force && this.tasksRequest) {
        // 同一时间只复用一个请求，避免用户连点导航时触发重复拉取。
        return this.tasksRequest
      }

      if (!force && isCacheFresh(this.tasksLoadedAt)) {
        return this.tasks
      }

      this.loadingTasks = true
      this.tasksLoadError = null

      const request = listTasks()
        .then((tasks) => {
          this.tasks = ensureArray(tasks)
          this.tasksLoadedAt = Date.now()
          return this.tasks
        })
        .catch((error) => {
          this.tasksLoadError = extractErrorMessage(error, '任务列表加载失败')
          throw error
        })
        .finally(() => {
          if (this.tasksRequest === request) {
            this.tasksRequest = null
          }
          this.loadingTasks = false
        })

      this.tasksRequest = request
      return request
    },

    async fetchModels(options?: { force?: boolean }) {
      // 拉取模型中心数据，并利用短 TTL 缓存降低页面切换时的请求量。
      const force = options?.force ?? false

      if (!force && this.modelsRequest) {
        return this.modelsRequest
      }

      if (!force && isCacheFresh(this.modelsLoadedAt)) {
        return this.models
      }

      this.loadingModels = true
      this.modelsLoadError = null

      const request = listModels()
        .then((models) => {
          this.models = localizeModelRecords(ensureArray(models))
          this.modelsLoadedAt = Date.now()
          return this.models
        })
        .catch((error) => {
          this.modelsLoadError = extractErrorMessage(error, '模型列表加载失败')
          throw error
        })
        .finally(() => {
          if (this.modelsRequest === request) {
            this.modelsRequest = null
          }
          this.loadingModels = false
        })

      this.modelsRequest = request
      return request
    },

    async fetchHistory(options?: { force?: boolean }) {
      // 历史记录用于历史中心和当前任务结果预览，两处共用同一份缓存。
      const force = options?.force ?? false

      if (!force && this.historyRequest) {
        return this.historyRequest
      }

      if (!force && isCacheFresh(this.historyLoadedAt)) {
        this.syncCurrentAssets()
        return this.history
      }

      this.loadingHistory = true
      this.historyLoadError = null

      const request = listAssetHistory()
        .then((history) => {
          this.history = ensureArray(history)
          this.historyLoadedAt = Date.now()
          this.syncCurrentAssets()
          return this.history
        })
        .catch((error) => {
          this.historyLoadError = extractErrorMessage(error, '历史记录加载失败')
          throw error
        })
        .finally(() => {
          if (this.historyRequest === request) {
            this.historyRequest = null
          }
          this.loadingHistory = false
        })

      this.historyRequest = request
      return request
    },

    async fetchHistoryPage(query: AssetHistoryPageQuery) {
      const normalizedQuery: AssetHistoryPageQuery = {
        page: query.page > 0 ? query.page : 1,
        page_size: query.page_size > 0 ? query.page_size : 10,
        prompt_keyword: query.prompt_keyword ?? '',
        model_name: query.model_name ?? '',
        status: query.status ?? 'all',
        min_total_score: query.min_total_score ?? 0,
      }
      const requestToken = this.historyPageRequestToken + 1
      this.historyPageRequestToken = requestToken
      this.historyPage = normalizedQuery.page
      this.historyPageSize = normalizedQuery.page_size
      this.loadingHistoryPage = true
      this.historyPageLoadError = null

      try {
        const result = await listAssetHistoryPage(normalizedQuery)
        if (this.historyPageRequestToken !== requestToken) {
          return result
        }

        const safePage = ensureHistoryPage(result)
        this.historyPageItems = safePage.items
        this.historyPage = safePage.page
        this.historyPageSize = safePage.page_size
        this.historyTotal = safePage.total
        this.historyTotalPages = safePage.total_pages
        return safePage
      } catch (error) {
        if (this.historyPageRequestToken === requestToken) {
          this.historyPageLoadError = extractErrorMessage(error, '历史分页加载失败')
        }
        throw error
      } finally {
        if (this.historyPageRequestToken === requestToken) {
          this.loadingHistoryPage = false
        }
      }
    },

    async refreshTask(taskId: number) {
      if (this.taskRequests[taskId]) {
        return this.taskRequests[taskId]
      }

      this.loadingTask = true
      this.taskLoadError = null

      const request = (async () => {
        // 详情与审计并行拉取，保证进度卡片和状态时间线能一起刷新。
        const [task, auditEvents] = await Promise.all([getTask(taskId), listTaskAuditEvents(taskId)])
        this.currentTask = task
        this.currentTaskAudit = ensureArray(auditEvents)
        if (this.currentTask.status === 'completed') {
          await this.fetchHistory({ force: true })
        }
        return this.currentTask
      })()
        .catch((error) => {
          this.taskLoadError = extractErrorMessage(error, `任务 #${taskId} 加载失败`)
          throw error
        })
        .finally(() => {
          delete this.taskRequests[taskId]
          this.loadingTask = Object.keys(this.taskRequests).length > 0
        })

      this.taskRequests[taskId] = request
      return request
    },

    syncCurrentAssets() {
      if (!this.currentTask) {
        this.currentAssets = []
        return
      }
      // 当前工作台只展示“当前任务”的资产切片，历史中心再展示完整列表。
      this.currentAssets = dedupeCurrentTaskAssets(
        ensureArray(this.history).filter((item) => item.job_id === this.currentTask?.id),
      )
    },

    async fetchTaskAudit(taskId: number) {
      // 独立刷新任务审计，用于历史详情抽屉和审计页复用。
      this.currentTaskAudit = ensureArray(await listTaskAuditEvents(taskId))
      return this.currentTaskAudit
    },

    async fetchAssetDetail(assetId: number) {
      // 查询当前选中资产的详情，用于历史中心右侧抽屉。
      this.selectedAssetDetail = await getAssetDetail(assetId)
      return this.selectedAssetDetail
    },
  },
})
