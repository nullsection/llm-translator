#!/usr/bin/env bash
# One-time setup for macOS / Linux: installs uv + deps, downloads the chosen
# translation model and voices. Usage: ./setup.sh [600M|1.3B|3.3B]
# Note: Japanese *speech* (VOICEVOX) is Windows-only; on macOS/Linux Japanese
# still transcribes and translates, but stays text-only.
set -e
cd "$(dirname "$0")"
MODEL="${1:-1.3B}"
export PYTHONUTF8=1

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv ..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

echo "Installing Python dependencies ..."
uv sync

echo "Downloading model $MODEL + voices ..."
TRANSLATOR_NLLB_MODEL="$MODEL" uv run translator setup-models --model "$MODEL"

echo "Done. Launch with:  uv run translator gui"
