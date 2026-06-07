#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"
fi

export MOCK_MODE=true
export MOCK_SCENARIO="${MOCK_SCENARIO:-all_clear}"
export PYTHONPATH="$ROOT/backend"

python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BACK_PID=$!

cleanup() {
  kill "$BACK_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cd frontend
npm run dev -- --host 127.0.0.1 --port 5173