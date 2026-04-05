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

export function createGenerateTask(payload: GenerateTaskRequest) {
  return unwrap<GenerateTask>(http.post('/tasks/generate', payload))
}

export function getTask(taskId: number) {
  return unwrap<GenerateTask>(http.get(`/tasks/${taskId}`))
}

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

export function listAssetHistory() {
  return unwrap<AssetHistoryItem[]>(http.get('/assets/history'))
}

export function getAssetDetail(assetId: number) {
  return unwrap<AssetDetail>(http.get(`/assets/history/${assetId}`))
}

export function listTaskAuditEvents(taskId: number) {
  return unwrap<AuditEvent[]>(http.get(`/audit/tasks/${taskId}/events`))
}

export function listModels() {
  return unwrap<ModelRecord[]>(http.get('/models'))
}

export function buildImageUrl(filePath: string) {
  // 资产服务当前通过网关静态文件入口暴露图片，只需要传最终文件名即可访问。
  const imageName = filePath.split(/[\\/]/).pop()
  return imageName ? `/files/images/${encodeURIComponent(imageName)}` : ''
}
