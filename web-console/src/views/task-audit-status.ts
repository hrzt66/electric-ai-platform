const TASK_AUDIT_STATUS_LABELS: Record<string, string> = {
  queued: '排队中',
  pending: '待处理',
  planning: '规划中',
  preparing: '准备中',
  running: '进行中',
  generating: '生成中',
  scoring: '评分中',
  scored: '已完成',
  completed: '已完成',
  failed: '失败',
  canceled: '已取消',
  cancelled: '已取消',
}

export function localizeTaskAuditStatus(status?: string | null) {
  if (!status) {
    return '--'
  }

  return TASK_AUDIT_STATUS_LABELS[status] || status
}
