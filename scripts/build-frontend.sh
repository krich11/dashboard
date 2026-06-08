#!/usr/bin/env bash
# Build frontend/dist. Safe to run under sudo — uses SUDO_USER's nvm/npm.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="${FRONTEND_DIR:-$ROOT/frontend}"

run_as_build_user() {
  local cmd="$1"
  local build_user="${BUILD_AS_USER:-${SUDO_USER:-$(id -un)}}"

  if [[ "$(id -u)" -eq 0 && "$build_user" != "root" ]]; then
    sudo -u "$build_user" -H bash -lc "cd '$FRONTEND_DIR' && $cmd"
  else
    bash -lc "cd '$FRONTEND_DIR' && $cmd"
  fi
}

if ! run_as_build_user 'command -v npm >/dev/null'; then
  cat >&2 <<EOF
ERROR: npm not found for build user.

If you use nvm, run deploy without stripping your environment, or build first:
  cd $FRONTEND_DIR && npm ci && npm run build
  sudo $ROOT/scripts/deploy-production.sh --local --skip-build
EOF
  exit 1
fi

echo "==> Building frontend in $FRONTEND_DIR"
run_as_build_user 'npm ci && npm run build'
[[ -f "$FRONTEND_DIR/dist/index.html" ]] || {
  echo "ERROR: frontend build failed — dist/index.html missing" >&2
  exit 1
}
echo "==> frontend/dist ready"