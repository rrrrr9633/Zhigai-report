#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLIENT="${ZHIGAI_REMOTE_CLIENT:-$ROOT_DIR/scripts/remote_generate.py}"

select_python() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi

  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi

  return 1
}

python_bin="$(select_python || true)"
if [[ -z "$python_bin" ]]; then
  echo "未检测到 Python，无法调用远程生成客户端。" >&2
  exit 127
fi

exec "$python_bin" "$CLIENT" "$@"
