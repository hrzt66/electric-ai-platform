#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
logs_root="${ELECTRIC_AI_LOGS_ROOT:-$repo_root/.runtime-logs/mac}"
with_deps=0

usage() {
  cat <<'EOF'
Usage: ./scripts/mac/stop-platform.sh [--with-deps]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-deps)
      with_deps=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

pidfile_running() {
  local pidfile="$1"
  if [[ ! -f "$pidfile" ]]; then
    return 1
  fi

  local pid
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  if [[ -z "$pid" ]]; then
    return 1
  fi

  kill -0 "$pid" >/dev/null 2>&1
}

stop_pid_and_children() {
  local pid="$1"

  if command -v pgrep >/dev/null 2>&1; then
    local child_pids
    child_pids="$(pgrep -P "$pid" || true)"
    if [[ -n "$child_pids" ]]; then
      while IFS= read -r child_pid; do
        [[ -n "$child_pid" ]] || continue
        stop_pid_and_children "$child_pid"
      done <<<"$child_pids"
    fi
  fi

  if kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
    local deadline=$((SECONDS + 15))
    while kill -0 "$pid" >/dev/null 2>&1; do
      if (( SECONDS >= deadline )); then
        kill -9 "$pid" >/dev/null 2>&1 || true
        break
      fi
      sleep 1
    done
  fi
}

stop_pidfile() {
  local name="$1"
  local pidfile="$2"

  if ! pidfile_running "$pidfile"; then
    rm -f "$pidfile"
    return 1
  fi

  local pid
  pid="$(cat "$pidfile")"
  stop_pid_and_children "$pid"

  rm -f "$pidfile"
  echo "Stopped $name (pid: $pid)"
  return 0
}

stop_listener_on_port() {
  local port="$1"
  local name="$2"
  local pids

  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN -n -P 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    return 1
  fi

  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    stop_pid_and_children "$pid"
  done <<<"$pids"

  echo "Stopped $name via port $port"
  return 0
}

stopped_any=0
service_names=(
  auth-service
  model-service
  task-service
  asset-service
  audit-service
  monitor-service
  gateway-service
  python-api
  python-worker
  web-console
)

for name in "${service_names[@]}"; do
  if stop_pidfile "$name" "$logs_root/$name.pid"; then
    stopped_any=1
  fi
done

port_names=(
  "8081:auth-service"
  "8082:model-service"
  "8083:task-service"
  "8084:asset-service"
  "8085:audit-service"
  "8086:monitor-service"
  "8080:gateway-service"
  "8090:python-api"
  "5173:web-console"
)

for entry in "${port_names[@]}"; do
  port="${entry%%:*}"
  name="${entry#*:}"
  if stop_listener_on_port "$port" "$name"; then
    stopped_any=1
  fi
done

if [[ "$with_deps" -eq 1 ]]; then
  if command -v docker >/dev/null 2>&1; then
    "$repo_root/scripts/dev-down.sh" 2>/dev/null || docker compose -f "$repo_root/deploy/docker-compose.dependencies.yml" down >/dev/null 2>&1 || true
    echo "Dependency shutdown requested."
  else
    echo "Skipped dependency shutdown because docker is not available."
  fi
fi

if [[ "$stopped_any" -eq 0 ]]; then
  echo "No managed platform processes were running."
fi
