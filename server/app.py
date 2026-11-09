from __future__ import annotations

import argparse
import json
import mimetypes
import os
import random
import re
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from control import queue_control_request, validate_control_request

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DEFAULT_MASCOT_NAME = "娴宝"


def mock_payload(name: str) -> dict:
    if name == "status":
        total = 8 * 1024 ** 3
        used = int(total * 0.42)
        return {"timestamp": "mock", "hostname": "R1-NAS", "uptime_sec": 123456,
                "cpu": {"usage_percent": random.randint(15, 48), "temperature_c": 43, "load1": 0.52, "load5": 0.44, "load15": 0.31},
                "memory": {"total_bytes": total, "used_bytes": used, "available_bytes": total-used, "usage_percent": 42.0}, "storage": None}
    if name == "disks":
        return {"timestamp": "mock", "disks": [{"device": "/dev/sata2", "model": "IronWolf 8TB", "state": "active", "temperature_c": 28,
                 "health_passed": True, "reallocated_sectors": 0, "power_on_hours": 25460, "capacity_bytes": 8001563222016, "error": None}]}
    if name == "activity":
        return {"timestamp": "mock", "privacy_mode": "status_only", "active_users": 1, "activities": [{"id": "mock", "username": "演示用户",
                "action": "store_photos", "action_label": "正在存入照片", "state": "active", "state_label": "使用中", "rate_mib_sec": None, "progress_percent": None}]}
    return {"timestamp": "mock", "state": "normal", "score": 0, "window_sec": 10, "files_modified": 0, "files_renamed": 0,
            "files_deleted": 0, "extensions_changed": 0, "entropy_anomalies": 0, "write_mib_sec": 0.0,
            "source": {"kind": "unknown", "container_name": None, "pid": None, "command": None}, "sample_paths": [],
            "message": "文件活动正常", "auto_contained": False}


class Handler(SimpleHTTPRequestHandler):
    server_version = "XianBaoR1/0.4.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self) -> None:
        # The embedded display is a long-running kiosk. Never let it keep an
        # old frontend after the container has been updated.
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _settings(self) -> dict:
        source = self.server.config_dir / "settings.json"
        if not source.is_file():
            return {"mascot_name": DEFAULT_MASCOT_NAME, "configured": False}
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
            name = str(payload.get("mascot_name", DEFAULT_MASCOT_NAME)).strip()
            return {"mascot_name": name or DEFAULT_MASCOT_NAME, "configured": True}
        except (OSError, json.JSONDecodeError):
            return {"mascot_name": DEFAULT_MASCOT_NAME, "configured": False}

    def do_POST(self) -> None:
        endpoint = self.path.split("?", 1)[0]
        if endpoint == "/api/control":
            try:
                length = min(int(self.headers.get("Content-Length", "0")), 4096)
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                self._json({"ok": False, "error": "invalid payload"}, HTTPStatus.BAD_REQUEST)
                return
            action, error = validate_control_request(payload)
            if error or action is None:
                self._json({"ok": False, "error": error}, HTTPStatus.BAD_REQUEST)
                return
            if self.client_address[0] not in {"127.0.0.1", "::1"}:
                self._json({"ok": False, "error": "controls are only available on the built-in display"}, HTTPStatus.FORBIDDEN)
                return
            try:
                self._json(queue_control_request(self.server.control_dir, action), HTTPStatus.ACCEPTED)
            except OSError:
                self._json({"ok": False, "error": "control channel unavailable"}, HTTPStatus.SERVICE_UNAVAILABLE)
            return
        if endpoint != "/api/settings":
            self._json({"ok": False, "error": "unknown endpoint"}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 4096)
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            name = str(payload.get("mascot_name", "")).strip()
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._json({"ok": False, "error": "invalid payload"}, HTTPStatus.BAD_REQUEST)
            return
        if not 1 <= len(name) <= 12 or re.search(r"[\x00-\x1f<>]", name):
            self._json({"ok": False, "error": "name must contain 1 to 12 safe characters"}, HTTPStatus.BAD_REQUEST)
            return
        try:
            self.server.config_dir.mkdir(parents=True, exist_ok=True)
            target = self.server.config_dir / "settings.json"
            temp = target.with_suffix(".tmp")
            temp.write_text(json.dumps({"mascot_name": name}, ensure_ascii=False), encoding="utf-8")
            temp.replace(target)
        except OSError:
            self._json({"ok": False, "error": "settings storage is not writable"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._json({"mascot_name": name, "configured": True})

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/api/health":
            self._json({"ok": True, "version": "0.4.1", "agent": self.server.snapshot_dir.exists()})
            return
        if self.path.split("?", 1)[0] == "/api/settings":
            self._json(self._settings())
            return
        if self.path.split("?", 1)[0] == "/api/control":
            source = self.server.control_dir / "state.json"
            if source.is_file():
                try:
                    payload = json.loads(source.read_text(encoding="utf-8"))
                    payload["available"] = self.client_address[0] in {"127.0.0.1", "::1"}
                    self._json(payload)
                except (OSError, json.JSONDecodeError):
                    self._json({"state": "idle", "available": self.client_address[0] in {"127.0.0.1", "::1"}})
            else:
                self._json({"state": "idle", "available": self.client_address[0] in {"127.0.0.1", "::1"}})
            return
        if self.path.startswith("/api/"):
            name = self.path.split("?", 1)[0].removeprefix("/api/")
            if name not in {"status", "disks", "activity", "security"}:
                self._json({"ok": False, "error": "unknown endpoint"}, HTTPStatus.NOT_FOUND)
                return
            source = self.server.snapshot_dir / f"{name}.json"
            if self.server.mock:
                self._json(mock_payload(name))
            elif source.is_file():
                try:
                    self._json(json.loads(source.read_text(encoding="utf-8")))
                except (OSError, json.JSONDecodeError):
                    self._json({"ok": False, "error": "snapshot temporarily unavailable"}, HTTPStatus.SERVICE_UNAVAILABLE)
            else:
                self._json({"ok": False, "error": "collector is starting"}, HTTPStatus.SERVICE_UNAVAILABLE)
            return
        requested = self.path.split("?", 1)[0]
        if requested != "/" and not (STATIC_DIR / requested.lstrip("/")).is_file():
            self.path = "/index.html"
        super().do_GET()

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} {fmt % args}", flush=True)


class Server(ThreadingHTTPServer):
    def __init__(self, address, handler, snapshot_dir: Path, config_dir: Path, control_dir: Path, mock: bool):
        super().__init__(address, handler)
        self.snapshot_dir = snapshot_dir
        self.config_dir = config_dir
        self.control_dir = control_dir
        self.mock = mock


def main() -> None:
    parser = argparse.ArgumentParser(description="R1 NAS screen panel")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--snapshot-dir", default=os.environ.get("R1_PANEL_RUNTIME_DIR", "/runtime"))
    parser.add_argument("--config-dir", default=os.environ.get("R1_PANEL_CONFIG_DIR", "/config"))
    parser.add_argument("--control-dir", default=os.environ.get("R1_PANEL_CONTROL_DIR", "/control"))
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()
    mimetypes.add_type("application/javascript", ".js")
    server = Server((args.host, args.port), Handler, Path(args.snapshot_dir), Path(args.config_dir), Path(args.control_dir), args.mock)
    print(f"R1 Panel listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
