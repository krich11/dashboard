from fastapi.testclient import TestClient

from app.main import app
from app.services.discovery_targets import (
    parse_ipv6_delegated_prefixes,
    parse_rfc1918_route_prefixes,
    sample_hosts_from_prefix,
)

client = TestClient(app)


def test_discovery_prefixes_mock_mode():
    response = client.get("/api/v1/discovery/prefixes")
    assert response.status_code == 200
    prefixes = response.json()["prefixes"]
    assert "10.0.0.0/24" in prefixes
    assert any("/56" in p for p in prefixes)


def test_discovery_scan_default_ranges_mock_mode():
    response = client.post(
        "/api/v1/discovery/scan",
        json={"use_default_ranges": True, "targets": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scanned"] >= 1
    assert body["scan_prefixes"]
    assert body["candidates"][0]["fingerprint_methods"]


def test_discovery_scan_explicit_target_mock_mode():
    response = client.post(
        "/api/v1/discovery/scan",
        json={"use_default_ranges": False, "targets": ["10.0.0.50"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scanned"] == 1
    assert body["candidates"][0]["reachable"] is True


def test_parse_rfc1918_route_prefixes():
    sample = """
192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.10
10.0.0.0/8 via 192.168.1.1
8.8.8.0/24 via 192.168.1.1
172.16.5.0/24 dev eth1 proto kernel scope link
"""
    prefixes = parse_rfc1918_route_prefixes(sample)
    assert "192.168.1.0/24" in prefixes
    assert "172.16.5.0/24" in prefixes
    assert "8.8.8.0/24" not in prefixes


def test_parse_ipv6_delegated_prefixes():
    sample = """
2001:db8:1000::/56 dev eth0 proto kernel metric 256
fe80::/64 dev eth0 proto kernel metric 256
fd00::/48 dev eth0 proto kernel metric 256
2001:db8:dead::/64 dev eth0 proto kernel metric 256
"""
    prefixes = parse_ipv6_delegated_prefixes(sample)
    assert "2001:db8:1000::/56" in prefixes
    assert "2001:db8:dead::/64" in prefixes
    assert not any(p.startswith("fe80") for p in prefixes)
    assert not any(p.startswith("fd00") for p in prefixes)


def test_ipv6_scan_samples_first_hosts():
    hosts = sample_hosts_from_prefix("2001:db8:1000::/56", 4)
    assert len(hosts) == 4
    assert all(":" in h for h in hosts)