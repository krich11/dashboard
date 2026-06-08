import asyncio

from sqlalchemy.orm import Session

from app.collectors.base import DeviceConnector
from app.collectors.helpers import (
    ConnectorError,
    device_credentials,
    device_target,
    load_device,
    make_status,
    ping_host,
)
from app.schemas.device import DeviceStatusRead


class LinuxSSHConnector(DeviceConnector):
    connector_type = "linux_ssh"

    def __init__(self, db: Session) -> None:
        self.db = db

    async def _poll_paramiko(
        self, device_id: str, target: str, username: str, password: str
    ) -> DeviceStatusRead:
        import paramiko  # optional dependency

        def run() -> tuple[str, dict]:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(target, username=username, password=password, timeout=15)
            try:
                _, stdout, _ = client.exec_command("cat /proc/loadavg && free -m | awk '/Mem:/ {print $3,$2}'")
                output = stdout.read().decode("utf-8", errors="replace").strip()
                lines = [line for line in output.splitlines() if line.strip()]
                metrics: dict[str, float | int | str] = {}
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 3 and "load_1m" not in metrics:
                        try:
                            metrics["load_1m"] = float(parts[0])
                        except ValueError:
                            continue
                    if len(parts) == 2 and "mem_used_mb" not in metrics:
                        try:
                            used, total = int(parts[0]), int(parts[1])
                        except ValueError:
                            continue
                        metrics["mem_used_mb"] = used
                        metrics["mem_total_mb"] = total
                        metrics["mem_pct"] = round(used / total * 100, 1) if total else 0
                return "ok", metrics
            finally:
                client.close()

        overall, metrics = await asyncio.to_thread(run)
        return make_status(
            device_id,
            overall,
            message="Linux SSH poll succeeded",
            metrics=metrics,
            details={"connector": self.connector_type, "method": "ssh"},
        )

    async def poll(self, device_id: str) -> DeviceStatusRead:
        device = load_device(self.db, device_id)
        target = device_target(device)
        username, password = device_credentials(device)

        if username and password:
            try:
                import paramiko  # noqa: F401
            except ImportError as exc:
                raise ConnectorError("paramiko is required for Linux SSH polling") from exc
            return await self._poll_paramiko(device_id, target, username, password)

        reachable, _latency = await ping_host(target)
        if not reachable:
            return make_status(
                device_id,
                "down",
                message="Host unreachable (ping failed, no SSH credentials)",
                details={"connector": self.connector_type, "method": "ping"},
            )
        return make_status(
            device_id,
            "ok",
            message="Host reachable via ping (no SSH credentials configured)",
            details={"connector": self.connector_type, "method": "ping"},
        )