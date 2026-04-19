#!/usr/bin/env bash

set -euo pipefail

compose_file="deploy/docker-compose.dependencies.yml"

usage() {
  cat <<'EOF'
Usage: ./scripts/dev-down.sh [-f compose-file]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--compose-file)
      compose_file="${2:-}"
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

docker compose -p "$project_name" -f "$compose_file_path" down -v

echo "Development dependencies are stopped."
