from __future__ import annotations

import json
import os
from pathlib import Path


DEFAULTS = {
    "runtime_dir": "/runtime",
    "control_dir": "/control",
    "host_root": "/host",
    "smartctl_path": "/usr/bin/smartctl",
    "smbstatus_path": "/usr/local/packages/@appstore/SMBService/usr/bin/smbstatus",
    "status_poll_interval_sec": 3,
    "disk_poll_interval_sec": 15,
    "activity_poll_interval_sec": 2,
    "security_poll_interval_sec": 1,
    "security_window_sec": 10,
    "security_enabled": False,
    "inotify_max_watches": 131072,
    "inotify_max_queued_events": 65536,
    "monitor_paths": ["/host/volume2"],
    "avoid_spinup": True,
    "use_nsenter": True,
}


def load_config(path: str | None = None) -> dict:
    config = dict(DEFAULTS)
    selected = path or os.environ.get("R1_PANEL_CONFIG")
    if selected and Path(selected).is_file():
        with open(selected, "r", encoding="utf-8") as handle:
            config.update(json.load(handle))

    env_map = {
        "R1_PANEL_RUNTIME_DIR": "runtime_dir",
        "R1_PANEL_CONTROL_DIR": "control_dir",
        "R1_PANEL_HOST_ROOT": "host_root",
        "R1_PANEL_SMARTCTL": "smartctl_path",
        "R1_PANEL_SMBSTATUS": "smbstatus_path",
    }
    for env_name, key in env_map.items():
        if os.environ.get(env_name):
            config[key] = os.environ[env_name]
    if os.environ.get("R1_PANEL_MONITOR_PATHS"):
        config["monitor_paths"] = [item.strip() for item in os.environ["R1_PANEL_MONITOR_PATHS"].split(",") if item.strip()]
    if os.environ.get("R1_PANEL_USE_NSENTER"):
        config["use_nsenter"] = os.environ["R1_PANEL_USE_NSENTER"].lower() in {"1", "true", "yes"}
    return config
