#!/usr/bin/env bash

set -euo pipefail

compose_file="deploy/docker-compose.dependencies.yml"
timeout_seconds=120

usage() {
  cat <<'EOF'
Usage: ./scripts/dev-up.sh [-f compose-file] [-t timeout-seconds]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--compose-file)
      compose_file="${2:-}"
      shift 2
      ;;
    -t|--timeout)
      timeout_seconds="${2:-}"
      shift 2
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

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$compose_file" = /* ]]; then
  compose_file_path="$compose_file"
else
  compose_file_path="$repo_root/$compose_file"
fi

if [[ ! -f "$compose_file_path" ]]; then
  echo "Compose file not found: $compose_file_path" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required but was not found in PATH." >&2
  exit 1
fi

normalized_root="$(printf '%s' "${repo_root%/}" | tr '[:upper:]' '[:lower:]')"
if command -v shasum >/dev/null 2>&1; then
  repo_hash="$(printf '%s' "$normalized_root" | shasum -a 256 | awk '{print $1}')"
elif command -v sha256sum >/dev/null 2>&1; then
  repo_hash="$(printf '%s' "$normalized_root" | sha256sum | awk '{print $1}')"
else
  repo_hash="$(printf '%s' "$normalized_root" | openssl dgst -sha256 | awk '{print $2}')"
fi
project_name="electric-ai-${repo_hash:0:12}"

compose() {
  docker compose -p "$project_name" -f "$compose_file_path" "$@"
}

service_container_id() {
  local service="$1"
  local container_id
  container_id="$(compose ps -q "$service" | head -n1 | tr -d '\r')"
  if [[ -z "$container_id" ]]; then
    echo "Service '$service' is not running." >&2
    exit 1
  fi
  printf '%s\n' "$container_id"
}

wait_for_service_health() {
  local service="$1"
  local container_id
  local status
  local start_time

  container_id="$(service_container_id "$service")"
  start_time="$(date +%s)"

  while true; do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id" | tr -d '\r')"
    if [[ "$status" == "healthy" ]]; then
      echo "$service is healthy."
      return
    fi

    if (( "$(date +%s)" - start_time >= timeout_seconds )); then
      echo "Timed out waiting for service '$service' to become healthy." >&2
      exit 1
    fi

    sleep 2
  done
}

compose up -d mysql redis
wait_for_service_health mysql
wait_for_service_health redis

echo "Development dependencies are ready."
