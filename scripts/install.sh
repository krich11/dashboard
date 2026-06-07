#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
echo "==> Installing backend dependencies"
"$PYTHON" -m pip install -r backend/requirements.txt

echo "==> Seeding mock fixtures"
"$PYTHON" scripts/seed_mocks.py

mkdir -p data

export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"
fi

if command -v npm >/dev/null 2>&1; then
  echo "==> Installing and building frontend"
  cd frontend
  npm ci
  npm run build
  cd "$ROOT"
else
  echo "==> Skipping frontend build (npm not found)"
fi

echo "==> Done. Copy .env.example to .env, then run: make dev"