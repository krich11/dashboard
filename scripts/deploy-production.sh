#!/usr/bin/env bash
# Push code updates from this repo to the production dashboard server.
#
# On the production server:
#   ./scripts/deploy-production.sh --local
#
# From another machine:
#   ./scripts/deploy-production.sh --remote
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CONFIG_FILE="$ROOT/deploy/production.env"
DEPLOY_MODE=""
DRY_RUN=false
SKIP_BUILD=false
SKIP_RESTART=false
RUN_TESTS=false

PRODUCTION_SSH=""
PRODUCTION_SSH_OPTS=""
PRODUCTION_INSTALL_DIR="/opt/dashboard"
PRODUCTION_SERVICE_USER="dashboard"
PRODUCTION_PORT="8000"

usage() {
  cat <<EOF
Deploy dashboard updates to production.

  ./scripts/deploy-production.sh --local    # on the production server
  ./scripts/deploy-production.sh --remote   # from a dev machine over SSH

--local builds frontend with your npm/nvm, then uses sudo only to copy into
$PRODUCTION_INSTALL_DIR and restart dashboard.service.

Never overwritten: .env, data/, backups/, .venv/

Flags: --dry-run --skip-build --skip-restart --run-tests
EOF
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --local) DEPLOY_MODE=local; shift ;;
    --remote) DEPLOY_MODE=remote; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    --skip-build) SKIP_BUILD=true; shift ;;
    --skip-restart) SKIP_RESTART=true; shift ;;
    --run-tests) RUN_TESTS=true; shift ;;
    -h|--help) usage 0 ;;
    *) echo "Unknown option: $1" >&2; usage 1 ;;
  esac
done

log() { printf '==> %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
check_ok() { printf '  ok: %s\n' "$*"; }

require_deploy_mode() {
  if [[ -z "$DEPLOY_MODE" ]]; then
    cat >&2 <<EOF
ERROR: Pass --local or --remote.

  ./scripts/deploy-production.sh --local
  ./scripts/deploy-production.sh --remote

Production .env at $PRODUCTION_INSTALL_DIR/.env is never modified.
EOF
    exit 1
  fi
}

load_config() {
  if [[ "$DEPLOY_MODE" == remote ]]; then
    [[ -f "$CONFIG_FILE" ]] || die "Remote deploy needs $CONFIG_FILE (see deploy/production.env.example)"
    # shellcheck disable=SC1090
    source "$CONFIG_FILE"
    [[ -n "$PRODUCTION_SSH" ]] || die "Set PRODUCTION_SSH in $CONFIG_FILE"
    return
  fi

  if [[ -f "$CONFIG_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$CONFIG_FILE"
  fi
}

preflight_local_repo() {
  log "Preflight: repository"
  [[ -f "$ROOT/backend/app/main.py" ]] || die "Missing backend/app/main.py"
  [[ -f "$ROOT/backend/requirements.txt" ]] || die "Missing backend/requirements.txt"
  [[ -f "$ROOT/frontend/package.json" ]] || die "Missing frontend/package.json"
  command -v rsync >/dev/null || die "rsync is required"
  check_ok "source tree"

  if $RUN_TESTS; then
    log "Running backend tests"
    (cd "$ROOT/backend" && TESTING=true PYTHONPATH=. python3 -m pytest -q)
    check_ok "pytest"
  fi
}

preflight_local_deploy() {
  if [[ "$(id -u)" -eq 0 ]]; then
    die "Do not run the whole script with sudo. Run: ./scripts/deploy-production.sh --local"
  fi
  [[ -d "$PRODUCTION_INSTALL_DIR" ]] || die "$PRODUCTION_INSTALL_DIR missing — run: sudo ./scripts/setup-systemd.sh"
  [[ -f "$PRODUCTION_INSTALL_DIR/.env" ]] || die "$PRODUCTION_INSTALL_DIR/.env missing — deploy never creates or replaces .env"
  if ! sudo -n true 2>/dev/null; then
    log "sudo access required to copy files and restart dashboard.service"
    sudo -v || die "sudo required for local deploy"
  fi
  check_ok "production install at $PRODUCTION_INSTALL_DIR"
}

build_frontend() {
  if $SKIP_BUILD; then
    log "Skipping frontend build (--skip-build)"
    [[ -f "$ROOT/frontend/dist/index.html" ]] || die "frontend/dist missing"
    return
  fi
  "$ROOT/scripts/build-frontend.sh"
  check_ok "frontend/dist"
}

rsync_excludes() {
  cat <<'EOF'
--exclude=data/
--exclude=backups/
--exclude=.env
--exclude=.venv/
--exclude=.git/
--exclude=frontend/node_modules/
--exclude=deploy/production.env
EOF
}

finalize_install() {
  local install_dir="$1"
  local service_user="$2"
  local port="$3"

  log "Installing into $install_dir and restarting service"
  sudo bash -s <<REMOTE
set -euo pipefail
INSTALL_DIR="$install_dir"
SERVICE_USER="$service_user"
PORT="$port"
SKIP_RESTART="$SKIP_RESTART"

chown -R "\$SERVICE_USER:\$SERVICE_USER" "\$INSTALL_DIR"
chown "\$SERVICE_USER:\$SERVICE_USER" "\$INSTALL_DIR/.env"
chmod 0600 "\$INSTALL_DIR/.env"

if [[ -x "\$INSTALL_DIR/.venv/bin/pip" ]]; then
  sudo -u "\$SERVICE_USER" "\$INSTALL_DIR/.venv/bin/pip" install -r "\$INSTALL_DIR/backend/requirements.txt"
  sudo -u "\$SERVICE_USER" env PYTHONPATH="\$INSTALL_DIR/backend" \
    "\$INSTALL_DIR/.venv/bin/python" -c "from app.main import app; assert app is not None"
fi

if [[ "\$SKIP_RESTART" != "true" ]]; then
  systemctl restart dashboard.service
  sleep 2
  systemctl is-active --quiet dashboard.service
  curl -sf "http://127.0.0.1:\$PORT/health" | grep -q '"status":"ok"'
  PID=\$(systemctl show -p MainPID --value dashboard.service)
  USER=\$(ps -o user= -p "\$PID" | tr -d ' ')
  [[ "\$USER" == "\$SERVICE_USER" ]]
fi
REMOTE
  check_ok "installed and healthy"
}

deploy_local() {
  preflight_local_deploy
  log "Deploying to $PRODUCTION_INSTALL_DIR (preserving .env, data/, backups/, .venv/)"
  local -a flags=(-a --delete)
  $DRY_RUN && flags+=(--dry-run -nv)
  mapfile -t excludes < <(rsync_excludes)
  sudo rsync "${flags[@]}" "${excludes[@]}" \
    "$ROOT/backend" "$ROOT/frontend" "$ROOT/mocks" "$ROOT/scripts" "$ROOT/deploy" \
    "$ROOT/README.md" "$ROOT/Makefile" \
    "$PRODUCTION_INSTALL_DIR/"
  if [[ -d "$ROOT/frontend/dist" ]]; then
    sudo rsync "${flags[@]}" "$ROOT/frontend/dist/" "$PRODUCTION_INSTALL_DIR/frontend/dist/"
  fi
  $DRY_RUN && return
  finalize_install "$PRODUCTION_INSTALL_DIR" "$PRODUCTION_SERVICE_USER" "$PRODUCTION_PORT"
}

deploy_remote() {
  local ssh_opts=()
  if [[ -n "$PRODUCTION_SSH_OPTS" ]]; then
    # shellcheck disable=SC2206
    ssh_opts=($PRODUCTION_SSH_OPTS)
  fi

  log "Preflight: SSH to $PRODUCTION_SSH"
  ssh "${ssh_opts[@]}" -o BatchMode=yes "$PRODUCTION_SSH" "echo ok" >/dev/null \
    || die "Cannot SSH to $PRODUCTION_SSH"
  check_ok "ssh"

  local staging="/tmp/dashboard-deploy-$$"
  mapfile -t excludes < <(rsync_excludes)
  local -a flags=(-az)
  $DRY_RUN && flags+=(--dry-run -nv)
  rsync "${flags[@]}" "${excludes[@]}" -e "ssh ${PRODUCTION_SSH_OPTS:-}" \
    "$ROOT/backend" "$ROOT/frontend" "$ROOT/mocks" "$ROOT/scripts" "$ROOT/deploy" \
    "$ROOT/README.md" "$ROOT/Makefile" \
    "${PRODUCTION_SSH}:${staging}/"
  if [[ -d "$ROOT/frontend/dist" ]]; then
    rsync "${flags[@]}" -e "ssh ${PRODUCTION_SSH_OPTS:-}" \
      "$ROOT/frontend/dist/" "${PRODUCTION_SSH}:${staging}/frontend/dist/"
  fi
  $DRY_RUN && return

  ssh "${ssh_opts[@]}" "$PRODUCTION_SSH" "sudo bash -s" <<REMOTE
set -euo pipefail
INSTALL_DIR="$PRODUCTION_INSTALL_DIR"
SERVICE_USER="$PRODUCTION_SERVICE_USER"
PORT="$PRODUCTION_PORT"
STAGING="$staging"
SKIP_RESTART="$SKIP_RESTART"

rsync -a --delete --exclude data/ --exclude backups/ --exclude .env --exclude .venv/ \
  "\$STAGING/" "\$INSTALL_DIR/"
[[ -d "\$STAGING/frontend/dist" ]] && rsync -a "\$STAGING/frontend/dist/" "\$INSTALL_DIR/frontend/dist/"
rm -rf "\$STAGING"
chown -R "\$SERVICE_USER:\$SERVICE_USER" "\$INSTALL_DIR"
chown "\$SERVICE_USER:\$SERVICE_USER" "\$INSTALL_DIR/.env"
chmod 0600 "\$INSTALL_DIR/.env"
if [[ -x "\$INSTALL_DIR/.venv/bin/pip" ]]; then
  sudo -u "\$SERVICE_USER" "\$INSTALL_DIR/.venv/bin/pip" install -r "\$INSTALL_DIR/backend/requirements.txt"
fi
if [[ "\$SKIP_RESTART" != "true" ]]; then
  systemctl restart dashboard.service
  sleep 2
  systemctl is-active --quiet dashboard.service
  curl -sf "http://127.0.0.1:\$PORT/health" | grep -q '"status":"ok"'
fi
REMOTE
  check_ok "remote deploy"
}

main() {
  require_deploy_mode
  load_config
  preflight_local_repo
  build_frontend

  if [[ "$DEPLOY_MODE" == local ]]; then
    deploy_local
    log "Done: http://127.0.0.1:$PRODUCTION_PORT"
  else
    deploy_remote
    log "Done: http://${PRODUCTION_SSH#*@}:$PRODUCTION_PORT"
  fi
}

main