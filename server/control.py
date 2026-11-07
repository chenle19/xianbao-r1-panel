from __future__ import annotations

import json
import time
from pathlib import Path

from collectors.common import atomic_write_json, host_command, now_iso

ALLOWED_ACTIONS = {"screen_off", "shutdown"}


def validate_control_request(payload: object) -> tuple[str | None, str | None]:
    if not isinstance(payload, dict):
        return None, "invalid payload"
    action = str(payload.get("action", "")).strip()
    if action not in ALLOWED_ACTIONS:
        return None, "unsupported action"
    if action == "shutdown" and payload.get("confirm") != "shutdown":
        return None, "shutdown confirmation required"
    return action, None


def queue_control_request(control_dir: Path, action: str) -> dict:
    control_dir.mkdir(parents=True, exist_ok=True)
    request = control_dir / f"{action}.request"
    atomic_write_json(request, {"action": action, "requested_at": now_iso()})
    return {"ok": True, "action": action, "state": "queued"}


class HostControlProcessor:
    def __init__(self, config: dict):
        self.config = config
        self.control_dir = Path(config["control_dir"])
        self.control_dir.mkdir(parents=True, exist_ok=True)
        self.shutdown_request = self.control_dir / "shutdown.request"
        self.state_file = self.control_dir / "state.json"

    def poll(self) -> None:
        if not self.shutdown_request.is_file():
            return
        try:
            payload = json.loads(self.shutdown_request.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        self.shutdown_request.unlink(missing_ok=True)
        if payload.get("action") != "shutdown":
            return
        atomic_write_json(self.state_file, {"action": "shutdown", "state": "starting", "timestamp": now_iso()})
        time.sleep(1.0)
        result = host_command(self.config, ["/usr/syno/sbin/synopoweroff"], timeout=20)
        if result.returncode != 0:
            atomic_write_json(self.state_file, {
                "action": "shutdown",
                "state": "failed",
                "timestamp": now_iso(),
                "message": (result.stderr or result.stdout or "DSM shutdown command failed")[-400:],
            })
