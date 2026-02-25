#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/install.sh [--with-shell-hook]

Options:
  --with-shell-hook   Add codex wrapper to shell rc file (~/.zshrc or ~/.bashrc)
  -h, --help          Show this help
EOF
}

with_shell_hook="false"
for arg in "$@"; do
  case "$arg" in
    --with-shell-hook)
      with_shell_hook="true"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[install] unknown option: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bridge_root="$(cd "$script_dir/.." && pwd)"

echo "[install] bootstrap python runtime..."
"$bridge_root/slack-bridge-runtime/bootstrap.sh"

echo "[install] config file is not auto-generated."
echo "[install] use ./config.toml or ~/.codex/config.toml"

if [[ "$with_shell_hook" == "true" ]]; then
  "$script_dir/install-shell-hook.sh"
fi

echo "[install] done"
