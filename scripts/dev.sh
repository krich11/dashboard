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

BIND_HOST="${BIND_HOST:-0.0.0.0}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"

python3 -m uvicorn app.main:app --reload --host "$BIND_HOST" --port 8000 \
  >"$ROOT/data/dev-backend.log" 2>&1 &
BACK_PID=$!

cd "$ROOT/frontend"
npm run dev -- --host "$FRONTEND_HOST" --port 5173 >"$ROOT/data/dev-frontend.log" 2>&1 &
FRONT_PID=$!

echo "Datacenter Dashboard dev servers started (detached)."
echo "  Backend:  http://${BIND_HOST}:8000  PID $BACK_PID  log data/dev-backend.log"
echo "  Frontend: http://${FRONTEND_HOST}:5173  PID $FRONT_PID  log data/dev-frontend.log"
echo "  LAN: use this host's IP instead of 0.0.0.0 from other machines on the network."
echo "Stop with: kill $BACK_PID $FRONT_PID"