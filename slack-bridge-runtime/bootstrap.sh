#!/usr/bin/env bash
set -euo pipefail

runtime_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv_dir="$runtime_dir/.venv"
python_bin="${PYTHON_BIN:-python3}"

if [[ ! -x "$(command -v "$python_bin")" ]]; then
  echo "[slack-bridge-runtime] Python not found: $python_bin" >&2
  echo "[slack-bridge-runtime] set PYTHON_BIN to a Python 3.11+ executable" >&2
  exit 1
fi

if ! "$python_bin" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
  python_ver=$("$python_bin" -V 2>&1)
  echo "[slack-bridge-runtime] python version must be 3.11 or later (current: $python_ver)" >&2
  echo "[slack-bridge-runtime] set PYTHON_BIN to Python 3.11+ executable" >&2
  exit 1
fi

if [[ -x "$venv_dir/bin/python3" ]] && ! "$venv_dir/bin/python3" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
  rm -rf "$venv_dir"
fi

if [[ ! -x "$venv_dir/bin/python3" ]]; then
  "$python_bin" -m venv "$venv_dir"
fi

"$venv_dir/bin/python3" -m pip install --upgrade pip >/dev/null
"$venv_dir/bin/python3" -m pip install -r "$runtime_dir/requirements.txt" >/dev/null

echo "[slack-bridge-runtime] ready: $venv_dir"
