#!/usr/bin/env bash
# Install Datacenter Dashboard as a systemd service.
#
# Run from the repository root:
#   sudo ./scripts/setup-systemd.sh
#
# Install from this checkout without copying to /opt:
#   sudo ./scripts/setup-systemd.sh --install-dir "$(pwd)" --user "$(whoami)"
#
# Production layout under /opt/dashboard:
#   sudo ./scripts/setup-systemd.sh --deploy-opt
#
set -euo pipefail

ORIG_ARGS=("$@")
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

INSTALL_DIR="$ROOT"
SERVICE_USER=""
SERVICE_GROUP=""
DEPLOY_OPT=false
BIND_HOST="0.0.0.0"
PORT="8000"
PYTHON_BIN="${PYTHON:-python3}"
VENV_DIR=""
USER_SERVICE=false
START_SERVICE=true
INSTALL_BACKUP_TIMER=false

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir)
      INSTALL_DIR="$(cd "$2" && pwd)"
      shift 2
      ;;
    --user)
      SERVICE_USER="$2"
      shift 2
      ;;
    --group)
      SERVICE_GROUP="$2"
      shift 2
      ;;
    --bind-host)
      BIND_HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --python)
      PYTHON_BIN="$2"
      shift 2
      ;;
    --venv)
      VENV_DIR="$2"
      shift 2
      ;;
    --deploy-opt)
      DEPLOY_OPT=true
      INSTALL_DIR="/opt/dashboard"
      SERVICE_USER="dashboard"
      shift
      ;;
    --backup-timer)
      INSTALL_BACKUP_TIMER=true
      shift
      ;;
    --user-service)
      USER_SERVICE=true
      shift
      ;;
    --no-start)
      START_SERVICE=false
      shift
      ;;
    -h|--help)
      usage 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage 1
      ;;
  esac
done

if [[ "$(id -u)" -ne 0 ]]; then
  if ! $USER_SERVICE; then
    echo "No root — installing user systemd service (--user-service)." >&2
    USER_SERVICE=true
  fi
fi

user_systemctl() {
  export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
  export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"
  systemctl --user "$@"
}

if $USER_SERVICE; then
  INSTALL_DIR="$(cd "${INSTALL_DIR:-$ROOT}" && pwd)"
  SERVICE_USER="$(whoami)"
  SERVICE_GROUP="$(id -gn)"
else
  if [[ -z "$SERVICE_USER" ]]; then
    SERVICE_USER="dashboard"
  fi
  if [[ -z "$SERVICE_GROUP" ]]; then
    SERVICE_GROUP="$SERVICE_USER"
  fi
fi

if [[ ! -f "$ROOT/backend/app/main.py" ]]; then
  echo "Expected backend at $ROOT/backend" >&2
  exit 1
fi

if $DEPLOY_OPT; then
  echo "==> Deploying application tree to $INSTALL_DIR"
  if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --home "$INSTALL_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
  fi
  mkdir -p "$INSTALL_DIR/data" "$INSTALL_DIR/backups"
  install -d -o "$SERVICE_USER" -g "$SERVICE_GROUP" "$INSTALL_DIR"
  rsync -a --delete \
    --exclude data/ \
    --exclude backups/ \
    --exclude .git/ \
    --exclude frontend/node_modules/ \
    --exclude 'frontend/dist' \
    "$ROOT/backend" "$ROOT/frontend" "$ROOT/mocks" "$ROOT/scripts" "$ROOT/deploy" \
    "$ROOT/README.md" "$ROOT/Makefile" \
    "$INSTALL_DIR/"
  if [[ -d "$ROOT/frontend/dist" ]]; then
    rsync -a "$ROOT/frontend/dist/" "$INSTALL_DIR/frontend/dist/"
  fi
  if [[ -f "$ROOT/.env" ]]; then
    install -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0600 "$ROOT/.env" "$INSTALL_DIR/.env"
  elif [[ ! -f "$INSTALL_DIR/.env" ]]; then
    install -o "$SERVICE_USER" -g "$SERVICE_GROUP" -m 0600 "$ROOT/.env.example" "$INSTALL_DIR/.env"
  fi
  chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
else
  INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd)"
  echo "==> Using install directory $INSTALL_DIR (no file copy)"
  mkdir -p "$INSTALL_DIR/data" "$INSTALL_DIR/backups"
  if [[ ! -f "$INSTALL_DIR/.env" ]]; then
    if [[ -f "$ROOT/.env" ]]; then
      cp "$ROOT/.env" "$INSTALL_DIR/.env"
    else
      cp "$ROOT/.env.example" "$INSTALL_DIR/.env"
    fi
    chown "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR/.env" 2>/dev/null || true
    chmod 0600 "$INSTALL_DIR/.env"
  fi
  if ! id "$SERVICE_USER" &>/dev/null; then
    echo "Service user $SERVICE_USER does not exist. Create it or pass --user." >&2
    exit 1
  fi
  chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR/data" "$INSTALL_DIR/backups" 2>/dev/null || true
fi

if [[ ! -d "$INSTALL_DIR/frontend/dist" ]]; then
  echo "==> frontend/dist missing — build on the install host before starting the service:" >&2
  echo "    cd $INSTALL_DIR/frontend && npm ci && npm run build" >&2
fi

if [[ -z "$VENV_DIR" ]]; then
  VENV_DIR="$INSTALL_DIR/.venv"
fi

create_venv() {
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    return 0
  fi
  echo "==> Creating virtualenv at $VENV_DIR"
  if "$PYTHON_BIN" -m venv "$VENV_DIR" 2>/dev/null; then
    return 0
  fi
  local pyver
  pyver="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  echo "==> python3-venv required; installing python${pyver}-venv"
  if command -v apt-get >/dev/null 2>&1 && [[ "$(id -u)" -eq 0 ]]; then
    apt-get update -qq
    apt-get install -y "python${pyver}-venv" || apt-get install -y python3-venv
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    return 0
  fi
  echo "Install python3-venv or pass --python with a working interpreter." >&2
  return 1
}

if create_venv; then
  PYTHON_BIN="$VENV_DIR/bin/python"
  echo "==> Installing Python dependencies into $VENV_DIR"
  "$PYTHON_BIN" -m pip install --upgrade pip
  "$PYTHON_BIN" -m pip install -r "$INSTALL_DIR/backend/requirements.txt"
  chown -R "$SERVICE_USER:$SERVICE_GROUP" "$VENV_DIR" 2>/dev/null || true
else
  echo "==> Falling back to system Python ($PYTHON_BIN)"
  "$PYTHON_BIN" -m pip install -r "$INSTALL_DIR/backend/requirements.txt" --break-system-packages
  VENV_DIR=""
fi

if $USER_SERVICE; then
  UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
  UNIT_PATH="$UNIT_DIR/dashboard.service"
  mkdir -p "$UNIT_DIR"
  echo "==> Writing $UNIT_PATH"
  sed \
    -e "s|@INSTALL_DIR@|$INSTALL_DIR|g" \
    -e "s|@PYTHON@|$PYTHON_BIN|g" \
    -e "s|@BIND_HOST@|$BIND_HOST|g" \
    -e "s|@PORT@|$PORT|g" \
    "$ROOT/deploy/dashboard.user.service.in" >"$UNIT_PATH"

  user_systemctl daemon-reload
  user_systemctl enable dashboard.service

  if $START_SERVICE; then
    user_systemctl restart dashboard.service
    user_systemctl --no-pager --full status dashboard.service
  else
    echo "Unit installed. Start with: systemctl --user start dashboard"
  fi

  if sudo -n loginctl enable-linger "$(whoami)" 2>/dev/null; then
    echo "==> Enabled linger (service survives logout/reboot)."
  else
    echo "==> Note: run 'sudo loginctl enable-linger $(whoami)' so the service starts at boot."
  fi

  cat <<EOF

Dashboard user systemd service installed.

  Install dir : $INSTALL_DIR
  Service user: $SERVICE_USER
  URL         : http://<host>:$PORT

Useful commands:
  systemctl --user status dashboard
  journalctl --user -u dashboard -f
  systemctl --user restart dashboard

Set MOCK_MODE=false in $INSTALL_DIR/.env for live connectors.
EOF
else
  UNIT_PATH="/etc/systemd/system/dashboard.service"
  echo "==> Writing $UNIT_PATH"
  sed \
    -e "s|@INSTALL_DIR@|$INSTALL_DIR|g" \
    -e "s|@SERVICE_USER@|$SERVICE_USER|g" \
    -e "s|@SERVICE_GROUP@|$SERVICE_GROUP|g" \
    -e "s|@PYTHON@|$PYTHON_BIN|g" \
    -e "s|@BIND_HOST@|$BIND_HOST|g" \
    -e "s|@PORT@|$PORT|g" \
    "$ROOT/deploy/dashboard.service.in" >"$UNIT_PATH"

  if $INSTALL_BACKUP_TIMER; then
    sed "s|/opt/dashboard|$INSTALL_DIR|g" "$ROOT/deploy/dashboard-backup.service" \
      >/etc/systemd/system/dashboard-backup.service
    cp "$ROOT/deploy/dashboard-backup.timer" /etc/systemd/system/dashboard-backup.timer
  fi

  if [[ "$INSTALL_DIR" == "/opt/dashboard" ]]; then
    cp "$UNIT_PATH" "$ROOT/deploy/dashboard.service"
  fi

  systemctl daemon-reload
  systemctl enable dashboard.service

  if $START_SERVICE; then
    systemctl restart dashboard.service
    systemctl --no-pager --full status dashboard.service
  else
    echo "Unit installed. Start with: sudo systemctl start dashboard"
  fi

  if $INSTALL_BACKUP_TIMER; then
    systemctl enable --now dashboard-backup.timer
    echo "Backup timer enabled (daily)."
  fi

  cat <<EOF

Dashboard systemd service installed.

  Install dir : $INSTALL_DIR
  Service user: $SERVICE_USER
  URL         : http://<host>:$PORT

Useful commands:
  sudo systemctl status dashboard
  sudo journalctl -u dashboard -f
  sudo systemctl restart dashboard

Set MOCK_MODE=false in $INSTALL_DIR/.env for live connectors.
EOF
fi