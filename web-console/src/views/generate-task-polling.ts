type TaskPollingCandidate = {
  id: number
  status: string
} | null

const TERMINAL_TASK_STATUSES = new Set(['completed', 'failed', 'scored', 'canceled', 'cancelled'])

export function isTerminalTaskStatus(status?: string | null) {
  return typeof status === 'string' && TERMINAL_TASK_STATUSES.has(status)
}

export function shouldResumeTaskPolling(task: TaskPollingCandidate) {
  if (!task) {
    return false
  }

  return !isTerminalTaskStatus(task.status)
}
