import type { AuditEvent, GenerateTask } from '../../types/platform'

export type ProgressTone = 'info' | 'warning' | 'success' | 'danger'
export type ProgressPhaseState = 'done' | 'active' | 'pending' | 'failed'

export type ProgressPhase = {
  key: string
  label: string
  state: ProgressPhaseState
}

export type GenerationProgress = {
  percent: number
  tone: ProgressTone
  headline: string
  stageLabel: string
  detail: string
  updatedAt: string
  phases: ProgressPhase[]
}

const PHASE_LABELS = ['任务受理', '模型准备', '图像生成', '评分归档'] as const
const PHASE_PERCENTS = [12, 34, 68, 88, 100] as const

function normalize(value: string) {
  // 统一大小写和分隔符，方便把 status / stage / event_type 放在一起比较。
  return value.trim().toLowerCase().replace(/[_\s-]+/g, '.')
}

function includesAny(source: string, tokens: string[]) {
  // 判断某段状态文本是否命中了任意关键词。
  return tokens.some((token) => source.includes(token))
}

function sortAuditEvents(events: AuditEvent[]) {
  // 审计事件按时间倒序排列，便于后续直接取“最近一条事件”。
  return [...events].sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at))
}

function resolvePhaseIndex(task: GenerateTask, auditEvents: AuditEvent[]) {
  // 综合任务状态和最近审计事件，推断当前进度应该落在哪个阶段。
  const current = normalize(`${task.status}.${task.stage}`)
  const latestEvent = sortAuditEvents(auditEvents)[0]
  const latest = latestEvent ? normalize(latestEvent.event_type) : ''
  const context = `${current}.${latest}`

  if (includesAny(context, ['completed', 'done', 'finished'])) {
    return 4
  }

  if (includesAny(context, ['score', 'audit', 'asset.persist', 'sync'])) {
    return 3
  }

  if (includesAny(context, ['generating', 'generation', 'render', 'infer'])) {
    return 2
  }

  if (includesAny(context, ['model.prepare', 'prepare', 'loading', 'warmup'])) {
    return 1
  }

  return 0
}

function buildPhaseState(index: number, activePhaseIndex: number, taskStatus: string): ProgressPhaseState {
  // 根据当前活跃阶段和失败状态，给每个阶段计算 done/active/pending/failed。
  if (taskStatus === 'failed') {
    if (index < activePhaseIndex) {
      return 'done'
    }
    if (index === activePhaseIndex) {
      return 'failed'
    }
    return 'pending'
  }

  if (activePhaseIndex >= 4) {
    return 'done'
  }

  if (index < activePhaseIndex) {
    return 'done'
  }

  if (index === activePhaseIndex) {
    return 'active'
  }

  return 'pending'
}

function buildHeadline(taskStatus: string, phaseIndex: number) {
  // 生成进度卡片顶部的大标题文案。
  if (taskStatus === 'failed') {
    return '任务执行失败'
  }

  if (taskStatus === 'completed' || phaseIndex >= 4) {
    return '生成完成'
  }

  if (phaseIndex === 3) {
    return '评分与归档中'
  }

  if (phaseIndex === 2) {
    return '图像生成中'
  }

  if (phaseIndex === 1) {
    return '模型准备中'
  }

  return '任务排队中'
}

function buildDetail(task: GenerateTask, phaseIndex: number) {
  // 为当前进度阶段生成更具体的解释文案。
  if (task.status === 'failed') {
    return task.error_message || '运行时中断了当前任务，请查看右侧实时状态与审计轨迹。'
  }

  if (task.status === 'completed' || phaseIndex >= 4) {
    return '图像生成、质量评分和结果同步已经全部完成。'
  }

  if (phaseIndex === 3) {
    return '图像已经生成完成，系统正在评分、入库并同步最终结果。'
  }

  if (phaseIndex === 2) {
    return '模型正在执行真实生成流程，新的审计事件会持续推动进度更新。'
  }

  if (phaseIndex === 1) {
    return '模型权重和运行环境正在准备中，完成后会自动进入生成阶段。'
  }

  return '任务已经提交成功，当前正在等待运行时调度。'
}

export function formatAuditEventLabel(eventType: string) {
  // 把后端事件类型翻译成更适合前端展示的短标签。
  const normalized = normalize(eventType)

  if (includesAny(normalized, ['score', 'audit'])) {
    return '评分归档'
  }
  if (includesAny(normalized, ['generating', 'generation', 'render', 'infer'])) {
    return '图像生成'
  }
  if (includesAny(normalized, ['model.prepare', 'prepare', 'loading', 'warmup'])) {
    return '模型准备'
  }
  if (includesAny(normalized, ['completed', 'done', 'finished'])) {
    return '完成同步'
  }
  if (includesAny(normalized, ['queued', 'submit', 'accept'])) {
    return '任务受理'
  }
  if (includesAny(normalized, ['fail', 'error'])) {
    return '执行失败'
  }

  return eventType
}

export function getRecentAuditEvents(auditEvents: AuditEvent[], count = 3) {
  // 截取最近几条事件，在进度卡片底部做简洁展示。
  return sortAuditEvents(auditEvents).slice(0, count)
}

export function buildGenerationProgress(task: GenerateTask | null, auditEvents: AuditEvent[]) {
  // 组合任务状态和审计事件，生成进度卡片渲染所需的完整结构。
  if (!task) {
    return null
  }

  const phaseIndex = resolvePhaseIndex(task, auditEvents)
  const tone: ProgressTone =
    task.status === 'failed' ? 'danger' : task.status === 'completed' ? 'success' : phaseIndex >= 2 ? 'warning' : 'info'

  return {
    percent: PHASE_PERCENTS[phaseIndex],
    tone,
    headline: buildHeadline(task.status, phaseIndex),
    stageLabel: phaseIndex >= 4 ? '已完成' : PHASE_LABELS[Math.min(phaseIndex, PHASE_LABELS.length - 1)],
    detail: buildDetail(task, phaseIndex),
    updatedAt: task.updated_at,
    phases: PHASE_LABELS.map((label, index) => ({
      key: label,
      label,
      state: buildPhaseState(index, phaseIndex, task.status),
    })),
  } satisfies GenerationProgress
}
