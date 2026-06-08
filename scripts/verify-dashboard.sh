#!/usr/bin/env bash
# Post-deploy / autonomous verification for a running dashboard instance.
# Checks API health, collector state, and data the web UI widgets depend on.
#
# Usage:
#   ./scripts/verify-dashboard.sh
#   BASE_URL=http://127.0.0.1:8000 ./scripts/verify-dashboard.sh
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
FAILURES=0

log_ok() { printf '  ok: %s\n' "$*"; }
log_fail() { printf '  FAIL: %s\n' "$*" >&2; FAILURES=$((FAILURES + 1)); }

check_http() {
  local name="$1"
  local url="$2"
  local expect="${3:-}"
  local body
  if body="$(curl -sf "$url" 2>&1)"; then
    if [[ -n "$expect" && "$body" != *"$expect"* ]]; then
      log_fail "$name — expected substring: $expect"
      return
    fi
    log_ok "$name"
  else
    log_fail "$name — $body"
  fi
}

echo "==> Dashboard verification: $BASE_URL"

check_http "health" "$BASE_URL/health" '"status":"ok"'
check_http "frontend shell" "$BASE_URL/" '<div id="root">'

ASSET_PATH="$(curl -sf "$BASE_URL/" | sed -n 's/.*src="\(\/assets\/[^"]*\)".*/\1/p' | head -1)"
if [[ -n "$ASSET_PATH" ]]; then
  check_http "frontend bundle" "$BASE_URL$ASSET_PATH" ""
else
  log_fail "frontend bundle — could not parse asset path from index.html"
fi

PYTHONPATH="${PYTHONPATH:-}" python3 - "$BASE_URL" <<'PY' || FAILURES=$((FAILURES + 1))
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime

base = sys.argv[1].rstrip("/")
failures = 0


def get(path: str) -> dict | list:
    with urllib.request.urlopen(f"{base}{path}", timeout=15) as resp:
        return json.loads(resp.read().decode())


def fail(msg: str) -> None:
    global failures
    print(f"  FAIL: {msg}", file=sys.stderr)
    failures += 1


def ok(msg: str) -> None:
    print(f"  ok: {msg}")


try:
    info = get("/api/v1/system/info")
    if not info.get("collector_running"):
        fail("collector not running")
    else:
        ok("collector running")

    if info.get("mock_mode"):
        ok("mock mode (skipping production data checks)")
    else:
        reach = get("/api/v1/reachability/latest")
        if reach.get("overall") == "ok":
            for family in ("ipv4_targets", "ipv6_targets"):
                for target in reach.get(family, []):
                    if target.get("ok") and target.get("latency_ms") is None:
                        fail(f"reachability {target.get('target')} ok but latency_ms is null")
            ok("reachability latency present when targets are up")

        summary = get("/api/v1/status/high-level")
        total = summary.get("important_total", 0)
        up = summary.get("important_up", 0)
        down = summary.get("important_down", 0)
        if up + down != total:
            fail(f"high-level counts inconsistent: up={up} down={down} total={total}")
        else:
            ok("high-level important device counts consistent")

        devices = get("/api/v1/devices/with-status")
        stale_limit = 300
        now = datetime.now(UTC)
        for device in devices:
            if not device.get("connector_enabled"):
                continue
            status = device.get("status")
            if status is None:
                fail(f"{device.get('name')} connector enabled but has no status")
                continue
            ts = datetime.fromisoformat(status["timestamp"].replace("Z", "+00:00"))
            age = (now - ts.astimezone(UTC)).total_seconds()
            if age > stale_limit:
                fail(f"{device.get('name')} status stale ({int(age)}s old)")
        ok("connector-enabled devices have fresh status")

    collector = get("/api/v1/settings/collector/status")
    if not collector.get("running"):
        fail("collector status reports not running")
    else:
        ok("collector status endpoint")

except urllib.error.URLError as exc:
    fail(f"API request failed: {exc}")
except Exception as exc:  # noqa: BLE001
    fail(f"verification error: {exc}")

sys.exit(1 if failures else 0)
PY

echo
if [[ "$FAILURES" -eq 0 ]]; then
  echo "VERIFY SUCCEEDED"
  exit 0
fi

echo "VERIFY FAILED ($FAILURES check group(s))"
exit 1