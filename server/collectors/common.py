from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def atomic_write_json(path: str | Path, payload: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        temp_name = handle.name
    os.replace(temp_name, target)
    # Agent writes as root inside the hardware-access container.  The web
    # container mounts the runtime volume read-only under DSM's package UID,
    # so snapshots must be world-readable but never world-writable.
    os.chmod(target, 0o644)


def host_command(config: dict, argv: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    root = config.get("host_root", "/host").rstrip("/")
    if config.get("use_nsenter"):
        command = ["/usr/sbin/chroot", "/proc/1/root", *argv]
        env = os.environ.copy()
        env.pop("LD_LIBRARY_PATH", None)
    else:
        command = [root + argv[0] if argv[0].startswith("/") else argv[0], *argv[1:]]
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = ":".join([
            root + "/lib", root + "/lib64", root + "/usr/lib", root + "/usr/lib64",
            root + "/usr/local/packages/@appstore/SMBService/usr/lib",
            root + "/usr/local/packages/@appstore/SMBService/usr/lib/samba",
        ])
    process = subprocess.run(command, capture_output=True, timeout=timeout, check=False, env=env)

    def decode(data: bytes) -> str:
        for encoding in ("utf-8", "gb18030"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                pass
        return data.decode("utf-8", errors="replace")

    return subprocess.CompletedProcess(process.args, process.returncode, decode(process.stdout), decode(process.stderr))


def host_path(config: dict, absolute_path: str) -> Path:
    return Path(config.get("host_root", "/host")) / absolute_path.lstrip("/")
