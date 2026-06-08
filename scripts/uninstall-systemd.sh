#!/usr/bin/env bash
# Remove Datacenter Dashboard systemd units (system + user).
#
#   sudo ./scripts/uninstall-systemd.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run with sudo: sudo $ROOT/scripts/uninstall-systemd.sh" >&2
  exit 1
fi

echo "==> Stopping system service (if present)"
systemctl stop dashboard.service 2>/dev/null || true
systemctl disable dashboard.service 2>/dev/null || true
rm -f /etc/systemd/system/dashboard.service
systemctl stop dashboard-backup.timer 2>/dev/null || true
systemctl disable dashboard-backup.timer 2>/dev/null || true
rm -f /etc/systemd/system/dashboard-backup.{service,timer}
systemctl daemon-reload

for homedir in /home/* /root; do
  [[ -d "$homedir" ]] || continue
  user_unit="$homedir/.config/systemd/user/dashboard.service"
  if [[ -f "$user_unit" ]]; then
    user="$(basename "$homedir")"
    echo "==> Removing user service for $user"
    sudo -u "$user" XDG_RUNTIME_DIR="/run/user/$(id -u "$user" 2>/dev/null || echo 0)" \
      systemctl --user stop dashboard.service 2>/dev/null || true
    sudo -u "$user" XDG_RUNTIME_DIR="/run/user/$(id -u "$user" 2>/dev/null || echo 0)" \
      systemctl --user disable dashboard.service 2>/dev/null || true
    rm -f "$user_unit"
    rm -f "$homedir/.config/systemd/user/default.target.wants/dashboard.service"
  fi
done

echo "==> Dashboard systemd units removed."
echo "    Application files under /opt/dashboard were not deleted."