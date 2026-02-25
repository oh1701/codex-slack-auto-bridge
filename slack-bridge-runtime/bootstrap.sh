#!/usr/bin/env bash
set -euo pipefail

runtime_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv_dir="$runtime_dir/.venv"
python_bin="${PYTHON_BIN:-python3}"

if [[ ! -x "$venv_dir/bin/python3" ]]; then
  "$python_bin" -m venv "$venv_dir"
fi

"$venv_dir/bin/python3" -m pip install --upgrade pip >/dev/null
"$venv_dir/bin/python3" -m pip install -r "$runtime_dir/requirements.txt" >/dev/null

echo "[slack-bridge-runtime] ready: $venv_dir"
