#!/usr/bin/env bash
# Build frontend/dist using the current user's node/npm (nvm OK).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="${FRONTEND_DIR:-$ROOT/frontend}"

# If something invoked us as root via sudo, hand off to the real user.
if [[ "$(id -u)" -eq 0 && -n "${SUDO_USER:-}" && "$SUDO_USER" != "root" ]]; then
  exec sudo -u "$SUDO_USER" -H "$0"
fi

export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [[ -s "$NVM_DIR/nvm.sh" ]]; then
  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"
fi

command -v npm >/dev/null || {
  echo "ERROR: npm not found. Install Node (nvm recommended), then retry." >&2
  exit 1
}

echo "==> Building frontend in $FRONTEND_DIR"
cd "$FRONTEND_DIR"
npm ci
npm run build
[[ -f dist/index.html ]] || {
  echo "ERROR: frontend build failed" >&2
  exit 1
}
echo "==> frontend/dist ready"