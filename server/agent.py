from __future__ import annotations

import argparse
import signal
import time
from pathlib import Path

from collectors.activity import collect_activity
from collectors.common import atomic_write_json, now_iso
from collectors.disks import collect_disks
from collectors.security import SecurityMonitor
from collectors.system import SystemCollector
from config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="R1 NAS privileged collector agent")
    parser.add_argument("--config")
    args = parser.parse_args()
    config = load_config(args.config)
    runtime = Path(config["runtime_dir"])
    runtime.mkdir(parents=True, exist_ok=True)
    system = SystemCollector(config)
    security = SecurityMonitor(config) if config.get("security_enabled", False) else None
    if security:
        security.start()
    running = True

    def stop(_signum, _frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    due = {"status": 0.0, "disks": 0.0, "activity": 0.0, "security": 0.0}
    while running:
        now = time.monotonic()
        try:
            if now >= due["status"]:
                atomic_write_json(runtime / "status.json", system.collect())
                due["status"] = now + float(config["status_poll_interval_sec"])
            if now >= due["disks"]:
                atomic_write_json(runtime / "disks.json", collect_disks(config))
                due["disks"] = now + float(config["disk_poll_interval_sec"])
            if now >= due["activity"]:
                atomic_write_json(runtime / "activity.json", collect_activity(config))
                due["activity"] = now + float(config["activity_poll_interval_sec"])
            if now >= due["security"]:
                payload = security.snapshot() if security else {
                    "timestamp": now_iso(), "state": "normal", "score": 0,
                    "window_sec": int(config["security_window_sec"]), "files_modified": 0,
                    "files_renamed": 0, "files_deleted": 0, "extensions_changed": 0,
                    "entropy_anomalies": 0, "write_mib_sec": 0.0,
                    "source": {"kind": "unknown", "container_name": None, "pid": None, "command": None},
                    "sample_paths": [], "message": "文件行为监控暂未启用", "auto_contained": False,
                }
                atomic_write_json(runtime / "security.json", payload)
                due["security"] = now + float(config["security_poll_interval_sec"])
        except Exception as exc:
            print(f"collector error: {exc}", flush=True)
        time.sleep(0.2)


if __name__ == "__main__":
    main()
