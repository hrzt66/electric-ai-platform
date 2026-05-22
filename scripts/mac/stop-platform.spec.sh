#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
script_path="$repo_root/scripts/mac/stop-platform.sh"
tmp_dir="$(mktemp -d)"
dummy_pid=""

cleanup() {
  if [[ -n "$dummy_pid" ]] && kill -0 "$dummy_pid" >/dev/null 2>&1; then
    kill "$dummy_pid" >/dev/null 2>&1 || true
  fi
  rm -rf "$tmp_dir"
}

trap cleanup EXIT

sleep 60 &
dummy_pid="$!"
echo "$dummy_pid" >"$tmp_dir/python-worker.pid"

output="$(ELECTRIC_AI_LOGS_ROOT="$tmp_dir" "$script_path" 2>&1)"

if kill -0 "$dummy_pid" >/dev/null 2>&1; then
  echo "Expected dummy process $dummy_pid to be stopped." >&2
  exit 1
fi

if [[ -f "$tmp_dir/python-worker.pid" ]]; then
  echo "Expected python-worker.pid to be removed." >&2
  exit 1
fi

if [[ "$output" != *"Stopped python-worker"* ]]; then
  echo "Expected output to mention python-worker stop, got: $output" >&2
  exit 1
fi

echo "stop-platform spec passed"
