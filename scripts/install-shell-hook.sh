#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/install-shell-hook.sh [--rc <path>]

Options:
  --rc <path>   Target shell rc file (default: ~/.zshrc or ~/.bashrc by current shell)
  -h, --help    Show this help
EOF
}

rc_file=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --rc)
      if [[ $# -lt 2 ]]; then
        echo "[install-shell-hook] --rc requires a path" >&2
        exit 1
      fi
      rc_file="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[install-shell-hook] unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bridge_root="$(cd "$script_dir/.." && pwd)"

if [[ -z "$rc_file" ]]; then
  shell_name="$(basename "${SHELL:-zsh}")"
  case "$shell_name" in
    bash)
      rc_file="$HOME/.bashrc"
      ;;
    *)
      rc_file="$HOME/.zshrc"
      ;;
  esac
fi

mkdir -p "$(dirname "$rc_file")"
touch "$rc_file"

start_marker="# >>> codex-slack-auto-bridge >>>"
end_marker="# <<< codex-slack-auto-bridge <<<"
tmp_file="$(mktemp)"

awk -v start="$start_marker" -v end="$end_marker" '
  $0 == start { skip = 1; next }
  $0 == end { skip = 0; next }
  skip != 1 { print }
' "$rc_file" > "$tmp_file"

cat >> "$tmp_file" <<EOF

$start_marker
export CODEX_SLACK_BRIDGE_ROOT="$bridge_root"

codex() {
  local _codex_bin
  _codex_bin="\$(command -v codex)"
  if [[ -z "\$_codex_bin" ]]; then
    echo "[codex-slack-bridge] codex command not found" >&2
    return 127
  fi

  local _bridge_cmd="\$CODEX_SLACK_BRIDGE_ROOT/scripts/slack-codex-bridge.sh"
  local _bridge_pat="[s]lack_codex_bridge\\\\.py"
  local _bridge_log="\$CODEX_SLACK_BRIDGE_ROOT/log/slack-codex-bridge.log"

  if [[ -x "\$_bridge_cmd" ]] && ! pgrep -f "\$_bridge_pat" >/dev/null 2>&1; then
    mkdir -p "\$CODEX_SLACK_BRIDGE_ROOT/log"
    nohup "\$_bridge_cmd" >>"\$_bridge_log" 2>&1 </dev/null &
    sleep 0.2
  fi

  command "\$_codex_bin" "\$@"
}
$end_marker
EOF

mv "$tmp_file" "$rc_file"
echo "[install-shell-hook] updated: $rc_file"
echo "[install-shell-hook] run: source $rc_file"
