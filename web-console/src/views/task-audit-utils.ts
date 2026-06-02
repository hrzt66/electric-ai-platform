type ResolveAuditTaskIdInput = {
  routeTaskId?: number | null
}

export function resolveAuditTaskId(input: ResolveAuditTaskIdInput) {
  if (input.routeTaskId && input.routeTaskId > 0) {
    return input.routeTaskId
  }

  return null
}
