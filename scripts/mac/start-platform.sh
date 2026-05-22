#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
logs_root="$repo_root/.runtime-logs/mac"
mkdir -p "$logs_root"

runtime_root="${ELECTRIC_AI_RUNTIME_ROOT:-$repo_root/model}"
mysql_port="${MYSQL_PORT:-3307}"
redis_port="${REDIS_PORT:-6380}"
web_port="${WEB_PORT:-5173}"
python_port="${PYTHON_API_PORT:-8090}"
jwt_secret="${JWT_SECRET:-electric-ai-secret}"

mysql_dsn="root:root@tcp(127.0.0.1:${mysql_port})/electric_ai?charset=utf8mb4&parseTime=True&loc=Local"
redis_addr="127.0.0.1:${redis_port}"
redis_url="redis://127.0.0.1:${redis_port}/0"
image_output_dir="${IMAGE_OUTPUT_DIR:-$runtime_root/image}"

usage() {
  cat <<'EOF'
Usage: ./scripts/mac/start-platform.sh [--skip-web]
EOF
}

skip_web=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-web)
      skip_web=1
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

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Required command not found: $cmd" >&2
    exit 1
  fi
}

resolve_python_cmd() {
  local candidates=(
    "$repo_root/.venv/bin/python"
    "$repo_root/python-ai-service/.venv/bin/python"
  )
  local candidate

  for candidate in "${candidates[@]}"; do
    if [[ -x "$candidate" ]] && "$candidate" -m uvicorn --version >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done

  for candidate in python python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -m uvicorn --version >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done

  echo "No usable Python interpreter found with uvicorn installed." >&2
  echo "Tried: $repo_root/.venv/bin/python, $repo_root/python-ai-service/.venv/bin/python, python, python3" >&2
  exit 1
}

port_listening() {
  local port="$1"
  lsof -iTCP:"$port" -sTCP:LISTEN -n -P >/dev/null 2>&1
}

http_ready() {
  local url="$1"
  curl -fsS "$url" >/dev/null 2>&1
}

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

wait_http_ready() {
  local url="$1"
  local name="$2"
  local timeout_seconds="${3:-60}"
  local start
  start="$(date +%s)"

  while true; do
    if http_ready "$url"; then
      echo "$name is ready: $url"
      return 0
    fi

    if (( "$(date +%s)" - start >= timeout_seconds )); then
      echo "Timed out waiting for $name at $url" >&2
      exit 1
    fi

    sleep 2
  done
}

start_service() {
  local name="$1"
  local workdir="$2"
  local health_url="$3"
  shift 3
  local stdout_log="$logs_root/${name}.stdout.log"
  local stderr_log="$logs_root/${name}.stderr.log"

  if http_ready "$health_url"; then
    echo "$name already ready: $health_url"
    return 0
  fi

  : >"$stdout_log"
  : >"$stderr_log"

  (
    cd "$workdir"
    nohup env "$@" >"$stdout_log" 2>"$stderr_log" &
    echo $! >"$logs_root/${name}.pid"
  )

  wait_http_ready "$health_url" "$name" 60
}

require_cmd curl
require_cmd go
require_cmd npm

python_cmd="$(resolve_python_cmd)"
echo "Using Python interpreter: $python_cmd"

if command -v docker >/dev/null 2>&1; then
  "$repo_root/scripts/dev-up.sh"
else
  if port_listening "$mysql_port" && port_listening "$redis_port"; then
    echo "docker not found; reusing existing MySQL:${mysql_port} and Redis:${redis_port} listeners."
  else
    echo "docker not found and MySQL:${mysql_port} / Redis:${redis_port} are not both listening." >&2
    echo "Please start MySQL and Redis first, or install Docker so scripts/dev-up.sh can provision them." >&2
    exit 1
  fi
fi

start_service \
  "auth-service" \
  "$repo_root" \
  "http://127.0.0.1:8081/health" \
  APP_NAME=auth-service \
  HTTP_PORT=8081 \
  MYSQL_DSN="$mysql_dsn" \
  REDIS_ADDR="$redis_addr" \
  JWT_SECRET="$jwt_secret" \
  go run ./services/auth-service/cmd/server

start_service \
  "model-service" \
  "$repo_root" \
  "http://127.0.0.1:8082/health" \
  APP_NAME=model-service \
  HTTP_PORT=8082 \
  MYSQL_DSN="$mysql_dsn" \
  REDIS_ADDR="$redis_addr" \
  JWT_SECRET="$jwt_secret" \
  go run ./services/model-service/cmd/server

start_service \
  "task-service" \
  "$repo_root" \
  "http://127.0.0.1:8083/health" \
  APP_NAME=task-service \
  HTTP_PORT=8083 \
  MYSQL_DSN="$mysql_dsn" \
  REDIS_ADDR="$redis_addr" \
  JWT_SECRET="$jwt_secret" \
  go run ./services/task-service/cmd/server

start_service \
  "asset-service" \
  "$repo_root" \
  "http://127.0.0.1:8084/health" \
  APP_NAME=asset-service \
  HTTP_PORT=8084 \
  MYSQL_DSN="$mysql_dsn" \
  REDIS_ADDR="$redis_addr" \
  JWT_SECRET="$jwt_secret" \
  go run ./services/asset-service/cmd/server

start_service \
  "audit-service" \
  "$repo_root" \
  "http://127.0.0.1:8085/health" \
  APP_NAME=audit-service \
  HTTP_PORT=8085 \
  MYSQL_DSN="$mysql_dsn" \
  REDIS_ADDR="$redis_addr" \
  JWT_SECRET="$jwt_secret" \
  go run ./services/audit-service/cmd/server

start_service \
  "monitor-service" \
  "$repo_root" \
  "http://127.0.0.1:8086/health" \
  APP_NAME=monitor-service \
  HTTP_PORT=8086 \
  MYSQL_DSN="$mysql_dsn" \
  REDIS_ADDR="$redis_addr" \
  JWT_SECRET="$jwt_secret" \
  go run ./services/monitor-service/cmd/server

start_service \
  "gateway-service" \
  "$repo_root" \
  "http://127.0.0.1:8080/health" \
  APP_NAME=gateway-service \
  HTTP_PORT=8080 \
  JWT_SECRET="$jwt_secret" \
  AUTH_SERVICE_URL=http://127.0.0.1:8081 \
  MODEL_SERVICE_URL=http://127.0.0.1:8082 \
  TASK_SERVICE_URL=http://127.0.0.1:8083 \
  ASSET_SERVICE_URL=http://127.0.0.1:8084 \
  AUDIT_SERVICE_URL=http://127.0.0.1:8085 \
  MONITOR_SERVICE_URL=http://127.0.0.1:8086 \
  IMAGE_OUTPUT_DIR="$image_output_dir" \
  go run ./services/gateway-service/cmd/server

start_service \
  "python-api" \
  "$repo_root/python-ai-service" \
  "http://127.0.0.1:${python_port}/health" \
  ELECTRIC_AI_RUNTIME_ROOT="$runtime_root" \
  HF_HOME="$runtime_root/hf-home" \
  TASK_SERVICE_BASE_URL=http://127.0.0.1:8083 \
  ASSET_SERVICE_BASE_URL=http://127.0.0.1:8084 \
  AUDIT_SERVICE_BASE_URL=http://127.0.0.1:8085 \
  MODEL_SERVICE_BASE_URL=http://127.0.0.1:8082 \
  REDIS_URL="$redis_url" \
  PYTHONIOENCODING=utf-8 \
  "$python_cmd" -m uvicorn app.main:app --host 127.0.0.1 --port "$python_port"

{
  cd "$repo_root/python-ai-service"
  if pidfile_running "$logs_root/python-worker.pid"; then
    echo "python-worker already running."
  else
    : >"$logs_root/python-worker.stdout.log"
    : >"$logs_root/python-worker.stderr.log"
    nohup env \
      ELECTRIC_AI_RUNTIME_ROOT="$runtime_root" \
      HF_HOME="$runtime_root/hf-home" \
      TASK_SERVICE_BASE_URL=http://127.0.0.1:8083 \
      ASSET_SERVICE_BASE_URL=http://127.0.0.1:8084 \
      AUDIT_SERVICE_BASE_URL=http://127.0.0.1:8085 \
      MODEL_SERVICE_BASE_URL=http://127.0.0.1:8082 \
      REDIS_URL="$redis_url" \
      PYTHONIOENCODING=utf-8 \
      "$python_cmd" -m app.worker >"$logs_root/python-worker.stdout.log" 2>"$logs_root/python-worker.stderr.log" &
    echo $! >"$logs_root/python-worker.pid"
  fi
}

if [[ "$skip_web" -eq 0 ]]; then
  start_service \
    "web-console" \
    "$repo_root/web-console" \
    "http://127.0.0.1:${web_port}" \
    npm run dev -- --host 127.0.0.1 --port "$web_port"
fi

cat <<EOF
Platform started.
Gateway: http://127.0.0.1:8080
Monitor: http://127.0.0.1:8086/health
Python API: http://127.0.0.1:${python_port}/health
Web console: http://127.0.0.1:${web_port}
Logs: $logs_root
EOF
