#!/usr/bin/env bash
# Push code updates from this repo to the production dashboard server.
#
# On the production server (updates /opt/dashboard, never touches .env):
#   sudo ./scripts/deploy-production.sh
#
# From another machine (requires deploy/production.env with PRODUCTION_SSH):
#   ./scripts/deploy-production.sh
#
# Options:
#   --dry-run          rsync dry run only
#   --skip-build       skip npm run build
#   --skip-restart     sync + pip install, do not restart systemd
#   --run-tests        run backend pytest before deploy
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CONFIG_FILE="$ROOT/deploy/production.env"
LOCAL_MODE=false
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
  cat <<'EOF'
Deploy dashboard updates to production.

On this server (no config file needed):
  sudo ./scripts/deploy-production.sh

From a dev machine to a remote server:
  cp deploy/production.env.example deploy/production.env
  ./scripts/deploy-production.sh

Production /opt/dashboard/.env, data/, backups/, and .venv/ are never overwritten.
EOF
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --local) LOCAL_MODE=true; shift ;;
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

load_config() {
  if [[ -f "$CONFIG_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$CONFIG_FILE"
    return
  fi

  if $LOCAL_MODE || [[ -d "$PRODUCTION_INSTALL_DIR" ]]; then
    LOCAL_MODE=true
    log "Local deploy to $PRODUCTION_INSTALL_DIR (deploy/production.env not required)"
    log "Preserving production .env, data/, backups/, and .venv/"
    return
  fi

  die "Missing $CONFIG_FILE — for remote deploy, copy deploy/production.env.example and set PRODUCTION_SSH. On the production server, run: sudo $ROOT/scripts/deploy-production.sh"
}

require_local_root() {
  if $LOCAL_MODE && [[ "$(id -u)" -ne 0 ]]; then
    die "Deploy on this server requires sudo: sudo $ROOT/scripts/deploy-production.sh"
  fi
}

preflight_local() {
  log "Preflight: local repository"
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

build_frontend() {
  if $SKIP_BUILD; then
    log "Skipping frontend build (--skip-build)"
    [[ -f "$ROOT/frontend/dist/index.html" ]] || die "frontend/dist missing — build first or drop --skip-build"
    return
  fi
  command -v npm >/dev/null || die "npm is required to build frontend"
  log "Building frontend"
  cd "$ROOT/frontend"
  npm ci
  npm run build
  cd "$ROOT"
  [[ -f "$ROOT/frontend/dist/index.html" ]] || die "frontend build failed"
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

rsync_payload() {
  local dest="$1"
  local -a flags=(-a --delete)
  $DRY_RUN && flags+=(--dry-run -nv)
  mapfile -t excludes < <(rsync_excludes)
  rsync "${flags[@]}" "${excludes[@]}" \
    "$ROOT/backend" \
    "$ROOT/frontend" \
    "$ROOT/mocks" \
    "$ROOT/scripts" \
    "$ROOT/deploy" \
    "$ROOT/README.md" \
    "$ROOT/Makefile" \
    "$dest"
  if [[ -d "$ROOT/frontend/dist" ]]; then
    rsync "${flags[@]}" "$ROOT/frontend/dist/" "$dest/frontend/dist/"
  fi
}

finalize_install() {
  local install_dir="$1"
  local service_user="$2"
  local port="$3"

  log "Finalize on production host"
  [[ -d "$install_dir" ]] || die "Install dir missing: $install_dir"
  [[ -f "$install_dir/.env" ]] || die "Production .env missing at $install_dir/.env (not overwritten by deploy)"

  chown -R "$service_user:$service_user" "$install_dir"
  # Preserve production secrets — never replace .env
  chown "$service_user:$service_user" "$install_dir/.env"
  chmod 0600 "$install_dir/.env"

  if [[ -x "$install_dir/.venv/bin/pip" ]]; then
    log "Updating Python dependencies in venv"
    sudo -u "$service_user" "$install_dir/.venv/bin/pip" install -r "$install_dir/backend/requirements.txt"
    sudo -u "$service_user" env PYTHONPATH="$install_dir/backend" \
      "$install_dir/.venv/bin/python" -c "from app.main import app; assert app is not None"
    check_ok "venv import check"
  else
    warn "No venv at $install_dir/.venv — run sudo ./scripts/setup-systemd.sh on the server first"
  fi

  if ! $SKIP_RESTART; then
    log "Restarting dashboard.service"
    systemctl restart dashboard.service
    sleep 2
    systemctl is-active --quiet dashboard.service || {
      systemctl --no-pager status dashboard.service >&2 || true
      die "dashboard.service failed to start"
    }
    check_ok "service active"

    if command -v curl >/dev/null; then
      local health
      health="$(curl -sf "http://127.0.0.1:$port/health" || true)"
      [[ "$health" == *'"status":"ok"'* ]] || die "Health check failed: $health"
      check_ok "/health on port $port"
    fi

    local main_pid proc_user
    main_pid="$(systemctl show -p MainPID --value dashboard.service)"
    proc_user="$(ps -o user= -p "$main_pid" 2>/dev/null | tr -d ' ' || true)"
    [[ "$proc_user" == "$service_user" ]] || die "Service running as '$proc_user', expected '$service_user'"
    check_ok "process runs as $service_user"
  else
    log "Skipping restart (--skip-restart)"
  fi
}

deploy_local() {
  log "Local deploy to $PRODUCTION_INSTALL_DIR"
  [[ -f "$PRODUCTION_INSTALL_DIR/.env" ]] || die "Production .env not found at $PRODUCTION_INSTALL_DIR/.env — run setup-systemd.sh first; deploy will not create or replace .env"
  rsync_payload "$PRODUCTION_INSTALL_DIR/"
  $DRY_RUN && return
  finalize_install "$PRODUCTION_INSTALL_DIR" "$PRODUCTION_SERVICE_USER" "$PRODUCTION_PORT"
}

deploy_remote() {
  [[ -n "$PRODUCTION_SSH" ]] || die "Set PRODUCTION_SSH in $CONFIG_FILE"
  local ssh_opts=()
  if [[ -n "$PRODUCTION_SSH_OPTS" ]]; then
    # shellcheck disable=SC2206
    ssh_opts=($PRODUCTION_SSH_OPTS)
  fi

  log "Preflight: SSH connectivity to $PRODUCTION_SSH"
  ssh "${ssh_opts[@]}" -o BatchMode=yes "$PRODUCTION_SSH" "echo connected" >/dev/null \
    || die "Cannot SSH to $PRODUCTION_SSH (check key/agent and PRODUCTION_SSH)"
  check_ok "ssh $PRODUCTION_SSH"

  local staging="/tmp/dashboard-deploy-$$"
  log "Rsync to $PRODUCTION_SSH:$staging"
  mapfile -t excludes < <(rsync_excludes)
  local -a flags=(-az)
  $DRY_RUN && flags+=(--dry-run -nv)
  rsync "${flags[@]}" "${excludes[@]}" -e "ssh ${PRODUCTION_SSH_OPTS:-}" \
    "$ROOT/backend" \
    "$ROOT/frontend" \
    "$ROOT/mocks" \
    "$ROOT/scripts" \
    "$ROOT/deploy" \
    "$ROOT/README.md" \
    "$ROOT/Makefile" \
    "${PRODUCTION_SSH}:${staging}/"
  if [[ -d "$ROOT/frontend/dist" ]]; then
    rsync "${flags[@]}" -e "ssh ${PRODUCTION_SSH_OPTS:-}" \
      "$ROOT/frontend/dist/" "${PRODUCTION_SSH}:${staging}/frontend/dist/"
  fi

  $DRY_RUN && return

  log "Applying update on production host"
  ssh "${ssh_opts[@]}" "$PRODUCTION_SSH" "sudo bash -s" <<REMOTE
set -euo pipefail
INSTALL_DIR="$PRODUCTION_INSTALL_DIR"
SERVICE_USER="$PRODUCTION_SERVICE_USER"
PORT="$PRODUCTION_PORT"
STAGING="$staging"
SKIP_RESTART="$SKIP_RESTART"

rsync -a --delete \
  --exclude data/ \
  --exclude backups/ \
  --exclude .env \
  --exclude .venv/ \
  "\$STAGING/" "\$INSTALL_DIR/"
if [[ -d "\$STAGING/frontend/dist" ]]; then
  rsync -a "\$STAGING/frontend/dist/" "\$INSTALL_DIR/frontend/dist/"
fi
rm -rf "\$STAGING"

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

  check_ok "remote update applied"
  log "Deploy complete: http://${PRODUCTION_SSH#*@}:$PRODUCTION_PORT"
}

main() {
  load_config
  require_local_root
  preflight_local
  build_frontend

  if $LOCAL_MODE; then
    deploy_local
    log "Deploy complete: http://127.0.0.1:$PRODUCTION_PORT"
  else
    deploy_remote
  fi
}

main