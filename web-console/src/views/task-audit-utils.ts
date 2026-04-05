import type { AssetHistoryItem, GenerateTask } from '../types/platform'

type ResolveAuditTaskIdInput = {
  routeTaskId?: number | null
  currentTaskId?: number | null
  tasks?: GenerateTask[] | null
  history?: AssetHistoryItem[] | null
}

function toTimestamp(value: string) {
  const timestamp = Date.parse(value)
  return Number.isFinite(timestamp) ? timestamp : 0
}

function pickLatestTask(tasks: GenerateTask[]) {
  return [...tasks].sort((left, right) => {
    const updatedDiff = toTimestamp(right.updated_at) - toTimestamp(left.updated_at)
    if (updatedDiff !== 0) {
      return updatedDiff
    }

    return right.id - left.id
  })[0]
}

function pickLatestHistory(history: AssetHistoryItem[]) {
  return [...history].sort((left, right) => {
    const createdDiff = toTimestamp(right.created_at) - toTimestamp(left.created_at)
    if (createdDiff !== 0) {
      return createdDiff
    }

    return right.job_id - left.job_id
  })[0]
}

export function resolveAuditTaskId(input: ResolveAuditTaskIdInput) {
  if (input.routeTaskId && input.routeTaskId > 0) {
    return input.routeTaskId
  }

  if (input.currentTaskId && input.currentTaskId > 0) {
    return input.currentTaskId
  }

  const latestTask = pickLatestTask(Array.isArray(input.tasks) ? input.tasks : [])
  if (latestTask) {
    return latestTask.id
  }

  const latestHistory = pickLatestHistory(Array.isArray(input.history) ? input.history : [])
  return latestHistory?.job_id ?? null
}
