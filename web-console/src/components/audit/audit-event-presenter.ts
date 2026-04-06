import type { AuditEvent } from '../../types/platform'

export type PresentedAuditEvent = {
  title: string
  description: string
}

type PayloadRecord = Record<string, unknown>

const FIELD_LABELS: Record<string, string> = {
  job_id: '任务 ID',
  model_name: '模型',
  count: '数量',
  asset_count: '结果数量',
  error_message: '错误原因',
  runtime: '运行时',
  stage: '阶段',
  status: '状态',
}

function normalizeEventType(value: string) {
  return value.trim().toLowerCase().replace(/[_\s-]+/g, '.')
}

function includesAny(source: string, tokens: string[]) {
  return tokens.some((token) => source.includes(token))
}

function parsePayload(payloadJson: string): PayloadRecord | null {
  if (!payloadJson.trim()) {
    return null
  }

  try {
    const parsed = JSON.parse(payloadJson)
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? (parsed as PayloadRecord) : null
  } catch {
    return null
  }
}

function formatValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.map((item) => formatValue(item)).filter(Boolean).join('、')
  }

  if (typeof value === 'boolean') {
    return value ? '是' : '否'
  }

  if (value === null || value === undefined) {
    return ''
  }

  return String(value)
}

function joinSentence(parts: string[]) {
  const sentence = parts.filter(Boolean).join('，')
  return sentence ? `${sentence}。` : ''
}

function summarizePayload(payload: PayloadRecord | null) {
  if (!payload) {
    return ''
  }

  return joinSentence(
    Object.entries(payload)
      .map(([key, value]) => {
        const renderedValue = formatValue(value)
        if (!renderedValue) {
          return ''
        }

        return `${FIELD_LABELS[key] ?? key} ${renderedValue}`
      })
      .filter(Boolean),
  )
}

function resolveTitle(eventType: string) {
  const normalized = normalizeEventType(eventType)

  if (includesAny(normalized, ['task.preparing', 'task.queued', 'task.accepted', 'queued', 'accepted'])) {
    return '任务已受理'
  }

  if (includesAny(normalized, ['model.prepare', 'prepare', 'loading', 'warmup', 'downloading'])) {
    return '模型准备中'
  }

  if (includesAny(normalized, ['generation.completed'])) {
    return '图像生成完成'
  }

  if (includesAny(normalized, ['job.generating', 'generating', 'render', 'infer'])) {
    return '图像生成中'
  }

  if (includesAny(normalized, ['scoring', 'score', 'audit'])) {
    return '评分处理中'
  }

  if (includesAny(normalized, ['asset.persist', 'asset.persisted'])) {
    return '资产已持久化'
  }

  if (includesAny(normalized, ['persisting', 'persist', 'sync'])) {
    return '结果归档中'
  }

  if (includesAny(normalized, ['task.completed', 'completed', 'done', 'finished'])) {
    return '任务完成'
  }

  if (includesAny(normalized, ['task.failed', 'failed', 'error', 'exception'])) {
    return '任务失败'
  }

  return '审计事件'
}

function resolveDescription(eventType: string, payload: PayloadRecord | null, message: string) {
  const normalized = normalizeEventType(eventType)
  const modelName = formatValue(payload?.model_name)
  const count = formatValue(payload?.count)
  const assetCount = formatValue(payload?.asset_count)
  const errorMessage = formatValue(payload?.error_message) || message.trim()

  if (includesAny(normalized, ['task.preparing', 'task.queued', 'task.accepted', 'queued', 'accepted'])) {
    return modelName
      ? `系统已接收任务，正在为模型 ${modelName} 准备运行环境。`
      : '系统已接收任务，正在准备运行环境。'
  }

  if (includesAny(normalized, ['model.prepare', 'prepare', 'loading', 'warmup', 'downloading'])) {
    return modelName
      ? `模型 ${modelName} 正在加载权重并预热运行时，请稍候。`
      : '模型权重和运行时环境正在准备中，请稍候。'
  }

  if (includesAny(normalized, ['generation.completed'])) {
    return count
      ? `本次生成已完成，共输出 ${count} 张图像，正在进入评分与归档阶段。`
      : '图像生成已经完成，正在进入评分与归档阶段。'
  }

  if (includesAny(normalized, ['job.generating', 'generating', 'render', 'infer'])) {
    return '模型正在执行图像生成，本阶段通常耗时最长，请耐心等待。'
  }

  if (includesAny(normalized, ['scoring', 'score', 'audit'])) {
    return '系统正在根据视觉保真、文本一致、物理合理和构图美学等维度计算评分。'
  }

  if (includesAny(normalized, ['asset.persist', 'asset.persisted', 'persisting', 'persist', 'sync'])) {
    return assetCount
      ? `评分结果正在归档，当前共同步 ${assetCount} 条结果记录。`
      : '评分结果与图像资产正在归档，请稍候。'
  }

  if (includesAny(normalized, ['task.completed', 'completed', 'done', 'finished'])) {
    return assetCount
      ? `任务已完成，${assetCount} 张结果图及其评分记录已归档。`
      : '任务已完成，结果图和评分记录已经归档。'
  }

  if (includesAny(normalized, ['task.failed', 'failed', 'error', 'exception'])) {
    return errorMessage ? `任务执行失败：${errorMessage}。` : '任务执行失败，请查看运行时日志排查原因。'
  }

  const summarizedPayload = summarizePayload(payload)
  if (summarizedPayload) {
    return summarizedPayload
  }

  if (message.trim()) {
    return `${message.trim()}。`
  }

  return '该阶段已记录，但没有附加说明。'
}

export function presentAuditEvent(event: AuditEvent): PresentedAuditEvent {
  const payload = parsePayload(event.payload_json)

  return {
    title: resolveTitle(event.event_type),
    description: resolveDescription(event.event_type, payload, event.message),
  }
}
