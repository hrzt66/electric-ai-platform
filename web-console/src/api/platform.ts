import { http } from './http'

import type {
  ApiEnvelope,
  AssetDetail,
  AssetHistoryItem,
  AuditEvent,
  GenerateTask,
  GenerateTaskRequest,
  ModelRecord,
} from '../types/platform'

async function unwrap<T>(request: Promise<{ data: ApiEnvelope<T> }>): Promise<T> {
  // 网关统一返回 ApiEnvelope，这里集中解包，避免页面层反复写 response.data.data。
  const response = await request
  return response.data.data
}

// createGenerateTask 提交一条新的真实生成任务。
export function createGenerateTask(payload: GenerateTaskRequest) {
  return unwrap<GenerateTask>(http.post('/tasks/generate', payload))
}

// getTask 查询单个任务的最新状态。
export function getTask(taskId: number) {
  return unwrap<GenerateTask>(http.get(`/tasks/${taskId}`))
}

// listTasks 拉取任务列表，并显式关闭浏览器缓存。
export function listTasks() {
  return unwrap<GenerateTask[]>(
    http.get('/tasks', {
      params: {
        __rt: 'task-list-v2',
      },
      headers: {
        'Cache-Control': 'no-cache, no-store, max-age=0',
        Pragma: 'no-cache',
      },
    }),
  )
}

// listAssetHistory 拉取历史中心所需的资产列表。
export function listAssetHistory() {
  return unwrap<AssetHistoryItem[]>(http.get('/assets/history'))
}

// getAssetDetail 查询单个资产的详细信息。
export function getAssetDetail(assetId: number) {
  return unwrap<AssetDetail>(http.get(`/assets/history/${assetId}`))
}

// listTaskAuditEvents 拉取某个任务的审计时间线。
export function listTaskAuditEvents(taskId: number) {
  return unwrap<AuditEvent[]>(http.get(`/audit/tasks/${taskId}/events`))
}

// listModels 拉取模型中心展示用的模型目录。
export function listModels() {
  return unwrap<ModelRecord[]>(http.get('/models'))
}

export function buildImageUrl(filePath: string) {
  // 资产服务当前通过网关静态文件入口暴露图片，只需要传最终文件名即可访问。
  const imageName = filePath.split(/[\\/]/).pop()
  return imageName ? `/files/images/${encodeURIComponent(imageName)}` : ''
}
