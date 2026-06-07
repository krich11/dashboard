#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
FAILURES=0

check() {
  local name="$1"
  local url="$2"
  local expect="${3:-}"

  if response="$(curl -sf "$url" 2>&1)"; then
    if [[ -n "$expect" && "$response" != *"$expect"* ]]; then
      echo "FAIL $name — expected substring: $expect"
      FAILURES=$((FAILURES + 1))
    else
      echo "OK   $name"
    fi
  else
    echo "FAIL $name — $response"
    FAILURES=$((FAILURES + 1))
  fi
}

echo "Datacenter Dashboard smoke test"
echo "Target: $BASE_URL"
echo

check "health" "$BASE_URL/health" '"status":"ok"'
check "mock scenario api" "$BASE_URL/api/v1/settings/mock-scenario" '"scenario"'
check "prometheus metrics" "$BASE_URL/metrics" "dashboard_important_devices_total"
check "alert settings" "$BASE_URL/api/v1/settings/alerts" '"enabled"'
check "high-level status" "$BASE_URL/api/v1/status/high-level" "banner"
check "reachability latest" "$BASE_URL/api/v1/reachability/latest" "overall"
check "devices list" "$BASE_URL/api/v1/devices" '"name"'
check "default dashboard" "$BASE_URL/api/v1/dashboards/default" "widgets"
check "widget catalog" "$BASE_URL/api/v1/widgets/catalog" "UpDownOverallStatus"
check "collector status" "$BASE_URL/api/v1/settings/collector/status" "total_devices"
check "history settings" "$BASE_URL/api/v1/settings/history" "raw_days"
check "system info" "$BASE_URL/api/v1/system/info" '"version":"1.5.2"'
check "status history" "$BASE_URL/api/v1/status/history" "important_total"
check "devices export" "$BASE_URL/api/v1/devices/export" "hostname"

echo
if [[ "$FAILURES" -eq 0 ]]; then
  echo "All smoke checks passed."
  exit 0
fi

echo "$FAILURES check(s) failed."
exit 1