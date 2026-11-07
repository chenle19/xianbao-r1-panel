from __future__ import annotations

import glob
import socket
import time
from pathlib import Path

from .common import host_path, now_iso


class SystemCollector:
    def __init__(self, config: dict):
        self.config = config
        self._last_cpu: tuple[int, int] | None = None

    def _read(self, path: str) -> str:
        return host_path(self.config, path).read_text(encoding="utf-8", errors="replace")

    def _cpu_usage(self) -> float:
        values = [int(value) for value in self._read("/proc/stat").splitlines()[0].split()[1:]]
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        total = sum(values)
        if self._last_cpu is None:
            self._last_cpu = (idle, total)
            time.sleep(0.12)
            return self._cpu_usage()
        last_idle, last_total = self._last_cpu
        self._last_cpu = (idle, total)
        delta_total = max(1, total - last_total)
        return round(max(0.0, min(100.0, 100.0 * (1 - (idle - last_idle) / delta_total))), 1)

    def _temperature(self) -> int | None:
        base = str(host_path(self.config, "/sys/class/hwmon"))
        candidates: list[float] = []
        for name_path in glob.glob(base + "/hwmon*/name"):
            try:
                name = Path(name_path).read_text().strip().lower()
            except OSError:
                continue
            if name not in {"coretemp", "k10temp", "acpitz", "cpu_thermal"}:
                continue
            for temp_path in glob.glob(str(Path(name_path).parent / "temp*_input")):
                try:
                    value = float(Path(temp_path).read_text().strip()) / 1000
                    if 0 < value < 120:
                        candidates.append(value)
                except (OSError, ValueError):
                    pass
        return round(max(candidates)) if candidates else None

    def collect(self) -> dict:
        meminfo = {}
        for line in self._read("/proc/meminfo").splitlines():
            if ":" in line:
                key, raw = line.split(":", 1)
                meminfo[key] = int(raw.strip().split()[0]) * 1024
        total = meminfo.get("MemTotal", 0)
        available = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
        used = max(0, total - available)
        load = self._read("/proc/loadavg").split()
        uptime = float(self._read("/proc/uptime").split()[0])
        hostname_path = host_path(self.config, "/etc/hostname")
        hostname = hostname_path.read_text(errors="replace").strip() if hostname_path.exists() else socket.gethostname()
        return {
            "timestamp": now_iso(),
            "hostname": hostname,
            "uptime_sec": int(uptime),
            "cpu": {
                "usage_percent": self._cpu_usage(),
                "temperature_c": self._temperature(),
                "load1": float(load[0]),
                "load5": float(load[1]),
                "load15": float(load[2]),
            },
            "memory": {
                "total_bytes": total,
                "used_bytes": used,
                "available_bytes": available,
                "usage_percent": round(used / total * 100, 1) if total else 0,
            },
            "storage": None,
        }
