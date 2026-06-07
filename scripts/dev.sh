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

python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 \
  >"$ROOT/data/dev-backend.log" 2>&1 &
BACK_PID=$!

cd "$ROOT/frontend"
npm run dev -- --host 127.0.0.1 --port 5173 >"$ROOT/data/dev-frontend.log" 2>&1 &
FRONT_PID=$!

echo "Datacenter Dashboard dev servers started (detached)."
echo "  Backend:  http://127.0.0.1:8000  PID $BACK_PID  log data/dev-backend.log"
echo "  Frontend: http://127.0.0.1:5173  PID $FRONT_PID  log data/dev-frontend.log"
echo "Stop with: kill $BACK_PID $FRONT_PID"