#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DB_PATH="${ROOT}/data/dashboard.db"
rm -f "$DB_PATH"

export MOCK_MODE=true
export MOCK_SCENARIO="${MOCK_SCENARIO:-all_clear}"
export PYTHONPATH="$ROOT/backend"

python3 - <<'PY'
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.device import Device
from app.services.mock_scenario import set_mock_scenario
from app.services.seed import seed_from_mocks

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    seed_from_mocks(db)
    set_mock_scenario(db, "all_clear")
    count = db.query(Device).count()
    print(f"Reset complete: {count} devices, scenario=all_clear")
finally:
    db.close()
PY