from datetime import UTC, datetime, timedelta

from app.services.normalization import is_device_up, normalize_overall


def test_normalize_overall():
    assert normalize_overall("UP") == "ok"
    assert normalize_overall("critical") == "critical"
    assert normalize_overall("offline") == "down"


def test_is_device_up_stale():
    old = datetime.now(UTC) - timedelta(seconds=400)
    assert is_device_up("ok", old, staleness_sec=180) is False


def test_is_device_down_status():
    recent = datetime.now(UTC)
    assert is_device_up("down", recent, staleness_sec=180) is False