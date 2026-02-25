#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
codex_root="$(cd "$script_dir/.." && pwd)"

# Preferred portable runtime folder for repository distribution.
runtime_dir="$codex_root/slack-bridge-runtime"
runtime_bootstrap="$runtime_dir/bootstrap.sh"
runtime_venv_python="$runtime_dir/.venv/bin/python3"

if [[ ! -x "$runtime_venv_python" && -x "$runtime_bootstrap" ]]; then
  "$runtime_bootstrap" >/dev/null 2>&1 || true
fi

if [[ -x "$runtime_venv_python" ]]; then
  exec "$runtime_venv_python" "$script_dir/slack_codex_bridge.py" "$@"
fi

exec python3 "$script_dir/slack_codex_bridge.py" "$@"
