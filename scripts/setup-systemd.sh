#!/usr/bin/env bash
# Install Datacenter Dashboard as a system systemd service.
#
# MUST be run as root:
#   sudo ./scripts/setup-systemd.sh
#
# Optional:
#   sudo ./scripts/setup-systemd.sh --backup-timer
#   sudo ./scripts/uninstall-systemd.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

INSTALL_DIR="/opt/dashboard"
SERVICE_USER="dashboard"
SERVICE_GROUP="dashboard"
BIND_HOST="0.0.0.0"
PORT="8000"
PYTHON_BIN="${PYTHON:-/usr/bin/python3}"
VENV_DIR=""
START_SERVICE=true
INSTALL_BACKUP_TIMER=false
ERRORS=0

usage() {
  cat <<'EOF'
Install Datacenter Dashboard under systemd (runs as user "dashboard").

  sudo ./scripts/setup-systemd.sh [--backup-timer] [--no-start]

Removes any prior user-level dashboard unit, deploys to /opt/dashboard,
creates a venv, installs dependencies, validates twice, and starts the service.

Uninstall:
  sudo ./scripts/uninstall-systemd.sh
EOF
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backup-timer) INSTALL_BACKUP_TIMER=true; shift ;;
    --no-start) START_SERVICE=false; shift ;;
    --bind-host) BIND_HOST="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    -h|--help) usage 0 ;;
    *) echo "Unknown option: $1" >&2; usage 1 ;;
  esac
done

log() { printf '==> %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
warn() { printf 'WARN: %s\n' "$*" >&2; }
check_fail() { ERRORS=$((ERRORS + 1)); printf 'CHECK FAILED: %s\n' "$*" >&2; }
check_ok() { printf '  ok: %s\n' "$*"; }

require_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    cat >&2 <<EOF
This installer must run as root.

  sudo $ROOT/scripts/setup-systemd.sh

It will create the system user "dashboard", deploy to /opt/dashboard, and
install /etc/systemd/system/dashboard.service. The app never runs as root.
EOF
    exit 1
  fi
}

remove_user_units() {
  log "Removing any user-level dashboard units"
  for homedir in /home/* /root; do
    [[ -d "$homedir" ]] || continue
    unit="$homedir/.config/systemd/user/dashboard.service"
    [[ -f "$unit" ]] || continue
    user="$(basename "$homedir")"
    uid="$(id -u "$user" 2>/dev/null || echo "")"
    [[ -n "$uid" && -d "/run/user/$uid" ]] || continue
    log "  stopping user service for $user"
    sudo -u "$user" \
      XDG_RUNTIME_DIR="/run/user/$uid" \
      DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" \
      systemctl --user stop dashboard.service 2>/dev/null || true
    sudo -u "$user" \
      XDG_RUNTIME_DIR="/run/user/$uid" \
      DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" \
      systemctl --user disable dashboard.service 2>/dev/null || true
    rm -f "$unit"
    rm -f "$homedir/.config/systemd/user/default.target.wants/dashboard.service"
  done
}

preflight_source() {
  log "Preflight: source tree"
  local f
  for f in backend/app/main.py backend/requirements.txt frontend/package.json .env.example; do
    [[ -f "$ROOT/$f" ]] || die "Missing $ROOT/$f — run from the repository root."
    check_ok "found $f"
  done
}

preflight_tools() {
  log "Preflight: host tools"
  command -v "$PYTHON_BIN" >/dev/null || die "Python not found: $PYTHON_BIN"
  check_ok "python: $("$PYTHON_BIN" --version 2>&1)"
  command -v rsync >/dev/null || die "rsync is required"
  check_ok "rsync"
  command -v systemctl >/dev/null || die "systemctl is required"
  check_ok "systemctl"
  if command -v ss >/dev/null; then
    if ss -tln "sport = :$PORT" 2>/dev/null | grep -q LISTEN; then
      die "Port $PORT is already in use. Stop the conflicting service first."
    fi
    check_ok "port $PORT is free"
  fi
}

ensure_dashboard_user() {
  log "Ensuring system user $SERVICE_USER"
  if id "$SERVICE_USER" &>/dev/null; then
    check_ok "user $SERVICE_USER exists (uid $(id -u "$SERVICE_USER"))"
  else
    useradd --system --home-dir "$INSTALL_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
    check_ok "created user $SERVICE_USER"
  fi
  id "$SERVICE_USER" &>/dev/null || die "Failed to create user $SERVICE_USER"
  [[ "$(id -u "$SERVICE_USER")" -ne 0 ]] || die "Service user must not be root"
}

deploy_application() {
  log "Deploying application to $INSTALL_DIR"
  mkdir -p "$INSTALL_DIR/data" "$INSTALL_DIR/backups"
  rsync -a --delete \
    --exclude data/ \
    --exclude backups/ \
    --exclude .git/ \
    --exclude frontend/node_modules/ \
    --exclude '.venv/' \
    "$ROOT/backend" "$ROOT/frontend" "$ROOT/mocks" "$ROOT/scripts" "$ROOT/deploy" \
    "$ROOT/README.md" "$ROOT/Makefile" \
    "$INSTALL_DIR/"
  if [[ -d "$ROOT/frontend/dist" ]]; then
    rsync -a "$ROOT/frontend/dist/" "$INSTALL_DIR/frontend/dist/"
  fi
  chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
  check_ok "files deployed"
}

ensure_env_file() {
  log "Ensuring $INSTALL_DIR/.env"
  if [[ -f "$ROOT/.env" ]]; then
    install -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0600 "$ROOT/.env" "$INSTALL_DIR/.env"
  elif [[ ! -f "$INSTALL_DIR/.env" ]]; then
    install -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0600 "$ROOT/.env.example" "$INSTALL_DIR/.env"
  fi
  [[ -f "$INSTALL_DIR/.env" ]] || die ".env missing after install"
  check_ok ".env installed (mode 600, owner $SERVICE_USER)"
}

ensure_frontend_build() {
  log "Ensuring frontend production build"
  if [[ -f "$INSTALL_DIR/frontend/dist/index.html" ]]; then
    check_ok "frontend/dist already present"
    return
  fi
  command -v npm >/dev/null || die "npm required to build frontend/dist (or build before install)"
  log "  building frontend (npm ci && npm run build)"
  cd "$INSTALL_DIR/frontend"
  npm ci
  npm run build
  cd "$ROOT"
  chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR/frontend/dist"
  [[ -f "$INSTALL_DIR/frontend/dist/index.html" ]] || die "frontend build failed"
  check_ok "frontend/dist built"
}

ensure_python_venv() {
  log "Ensuring Python virtualenv"
  VENV_DIR="$INSTALL_DIR/.venv"
  local pyver
  pyver="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

  if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    if ! "$PYTHON_BIN" -m venv "$VENV_DIR" 2>/dev/null; then
      log "  installing python${pyver}-venv package"
      if command -v apt-get >/dev/null; then
        apt-get update -qq
        apt-get install -y "python${pyver}-venv" || apt-get install -y python3-venv
      else
        die "python3-venv is required (apt install python${pyver}-venv)"
      fi
      "$PYTHON_BIN" -m venv "$VENV_DIR"
    fi
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$VENV_DIR"
  fi

  log "  installing Python dependencies"
  sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install --upgrade pip
  sudo -u "$SERVICE_USER" "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/backend/requirements.txt"

  sudo -u "$SERVICE_USER" env PYTHONPATH="$INSTALL_DIR/backend" \
    "$VENV_DIR/bin/python" -c "from app.main import app; assert app is not None" \
    || die "Python import check failed in venv"
  check_ok "venv at $VENV_DIR"
}

install_systemd_unit() {
  log "Installing /etc/systemd/system/dashboard.service"
  sed \
    -e "s|@INSTALL_DIR@|$INSTALL_DIR|g" \
    -e "s|@SERVICE_USER@|$SERVICE_USER|g" \
    -e "s|@SERVICE_GROUP@|$SERVICE_GROUP|g" \
    -e "s|@PYTHON@|$VENV_DIR/bin/python|g" \
    -e "s|@BIND_HOST@|$BIND_HOST|g" \
    -e "s|@PORT@|$PORT|g" \
    "$ROOT/deploy/dashboard.service.in" >/etc/systemd/system/dashboard.service

  grep -q "^User=$SERVICE_USER$" /etc/systemd/system/dashboard.service \
    || die "Unit file missing User=$SERVICE_USER"
  grep -q "^Group=$SERVICE_GROUP$" /etc/systemd/system/dashboard.service \
    || die "Unit file missing Group=$SERVICE_GROUP"

  cp /etc/systemd/system/dashboard.service "$ROOT/deploy/dashboard.service"

  if $INSTALL_BACKUP_TIMER; then
    sed "s|/opt/dashboard|$INSTALL_DIR|g" "$ROOT/deploy/dashboard-backup.service" \
      >/etc/systemd/system/dashboard-backup.service
    cp "$ROOT/deploy/dashboard-backup.timer" /etc/systemd/system/dashboard-backup.timer
  fi

  systemctl daemon-reload
  systemctl enable dashboard.service
  check_ok "systemd unit installed and enabled"
}

verify_filesystem() {
  log "Verify pass 1: filesystem and permissions"
  ERRORS=0

  [[ -d "$INSTALL_DIR" ]] && check_ok "install dir exists" || check_fail "missing $INSTALL_DIR"
  [[ "$(stat -c '%U:%G' "$INSTALL_DIR")" == "$SERVICE_USER:$SERVICE_GROUP" ]] \
    && check_ok "install dir owned by $SERVICE_USER" \
    || check_fail "install dir ownership wrong: $(stat -c '%U:%G' "$INSTALL_DIR")"

  [[ -f "$INSTALL_DIR/.env" ]] && check_ok ".env exists" || check_fail ".env missing"
  [[ "$(stat -c '%a' "$INSTALL_DIR/.env")" == "600" ]] && check_ok ".env mode 600" || check_fail ".env not mode 600"
  [[ "$(stat -c '%U' "$INSTALL_DIR/.env")" == "$SERVICE_USER" ]] && check_ok ".env owned by $SERVICE_USER" || check_fail ".env owner wrong"

  [[ -x "$VENV_DIR/bin/python" ]] && check_ok "venv python executable" || check_fail "venv missing"
  [[ -f "$INSTALL_DIR/frontend/dist/index.html" ]] && check_ok "frontend dist present" || check_fail "frontend dist missing"

  sudo -u "$SERVICE_USER" test -w "$INSTALL_DIR/data" \
    && check_ok "$SERVICE_USER can write data/" \
    || check_fail "$SERVICE_USER cannot write data/"

  [[ $ERRORS -eq 0 ]] || die "Filesystem verification failed ($ERRORS checks)"
  log "Verify pass 1: all checks passed"
}

start_and_verify_runtime() {
  log "Starting service"
  if $START_SERVICE; then
    systemctl restart dashboard.service
    sleep 2
  else
    log "Skipping start (--no-start)"
    return
  fi

  log "Verify pass 2: runtime"
  ERRORS=0

  systemctl is-active --quiet dashboard.service \
    && check_ok "service is active" \
    || { check_fail "service not active"; systemctl --no-pager status dashboard.service >&2 || true; }

  local unit_user
  unit_user="$(systemctl show -p User --value dashboard.service)"
  [[ "$unit_user" == "$SERVICE_USER" ]] && check_ok "systemd User=$SERVICE_USER" || check_fail "systemd User=$unit_user"

  local main_pid
  main_pid="$(systemctl show -p MainPID --value dashboard.service)"
  if [[ "$main_pid" =~ ^[0-9]+$ && "$main_pid" -gt 0 ]]; then
    local proc_user
    proc_user="$(ps -o user= -p "$main_pid" | tr -d ' ')"
    [[ "$proc_user" == "$SERVICE_USER" ]] && check_ok "process $main_pid runs as $SERVICE_USER" \
      || check_fail "process $main_pid runs as $proc_user (expected $SERVICE_USER)"
  else
    check_fail "could not read MainPID"
  fi

  if command -v curl >/dev/null; then
    local health
    health="$(curl -sf "http://127.0.0.1:$PORT/health" || true)"
    [[ "$health" == *'"status":"ok"'* ]] && check_ok "/health returns ok" || check_fail "/health check failed: $health"
  else
    warn "curl not installed — skipping HTTP health check"
  fi

  if ss -tln "sport = :$PORT" 2>/dev/null | grep -q "0.0.0.0:$PORT"; then
    check_ok "listening on 0.0.0.0:$PORT"
  else
    check_fail "not listening on 0.0.0.0:$PORT"
  fi

  [[ $ERRORS -eq 0 ]] || die "Runtime verification failed ($ERRORS checks)"
  log "Verify pass 2: all checks passed"
  systemctl --no-pager --full status dashboard.service
}

finish_message() {
  cat <<EOF

Dashboard installed successfully.

  Install dir : $INSTALL_DIR
  Service user: $SERVICE_USER (not root)
  URL         : http://<host>:$PORT

Commands:
  sudo systemctl status dashboard
  sudo journalctl -u dashboard -f
  sudo systemctl restart dashboard
  sudo $ROOT/scripts/uninstall-systemd.sh

Edit $INSTALL_DIR/.env — set MOCK_MODE=false for live connectors.
EOF
}

main() {
  require_root
  remove_user_units
  preflight_source
  preflight_tools
  ensure_dashboard_user
  deploy_application
  ensure_env_file
  ensure_frontend_build
  ensure_python_venv
  install_systemd_unit
  verify_filesystem
  start_and_verify_runtime

  if $INSTALL_BACKUP_TIMER; then
    systemctl enable --now dashboard-backup.timer
    check_ok "backup timer enabled"
  fi

  finish_message
}

main