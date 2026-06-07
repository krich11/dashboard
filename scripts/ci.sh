#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Backend tests"
cd backend
TESTING=true PYTHONPATH=. python3 -m pytest -q
cd "$ROOT"

export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"
fi

echo "==> Frontend tests and build"
cd frontend
npm ci
npm run test
npm run build

echo "==> CI checks passed"