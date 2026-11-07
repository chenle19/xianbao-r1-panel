from __future__ import annotations

import ctypes
import json
import math
import os
import select
import struct
import threading
import time
from collections import deque
from pathlib import Path

from .common import host_command, now_iso


IN_MODIFY = 0x00000002
IN_CLOSE_WRITE = 0x00000008
IN_MOVED_FROM = 0x00000040
IN_MOVED_TO = 0x00000080
IN_CREATE = 0x00000100
IN_DELETE = 0x00000200
IN_ISDIR = 0x40000000
WATCH_MASK = IN_MODIFY | IN_CLOSE_WRITE | IN_MOVED_FROM | IN_MOVED_TO | IN_CREATE | IN_DELETE
FAN_CLOEXEC = 0x00000001
FAN_NONBLOCK = 0x00000002
FAN_MARK_ADD = 0x00000001
FAN_MARK_MOUNT = 0x00000010
FAN_CLOSE_WRITE = 0x00000008
FAN_Q_OVERFLOW = 0x00004000
FANOTIFY_METADATA_VERSION = 3
SUSPICIOUS_SUFFIXES = {".locked", ".encrypted", ".crypt", ".enc", ".lockbit", ".wncry"}


class SecurityMonitor:
    def __init__(self, config: dict):
        self.config = config
        self.window = int(config.get("security_window_sec", 10))
        self.events: deque[dict] = deque(maxlen=12000)
        self._lock = threading.Lock()
        self._watches: dict[int, str] = {}
        self._renames: dict[int, tuple[float, str, bool]] = {}
        self._created: dict[str, float] = {}
        self._fd = -1
        self._error: str | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="security-monitor", daemon=True)
        self._thread.start()

    def _add_tree(self, root: str) -> None:
        for current, dirs, _files in os.walk(root):
            dirs[:] = [name for name in dirs if not name.startswith("@") and name not in {"#recycle", ".snapshot", ".SynologyWorkingDirectory"}]
            if len(self._watches) >= int(self.config.get("inotify_max_watches", 131072)) - 1024:
                break
            wd = self._libc.inotify_add_watch(self._fd, os.fsencode(current), WATCH_MASK)
            if wd >= 0:
                self._watches[wd] = current

    def _run(self) -> None:
        try:
            self._ensure_inotify_limits()
            self._run_inotify()
        except Exception as exc:
            self._error = str(exc)[:240]

    def _ensure_inotify_limits(self) -> None:
        values = {
            "/proc/sys/fs/inotify/max_user_watches": int(self.config.get("inotify_max_watches", 131072)),
            "/proc/sys/fs/inotify/max_queued_events": int(self.config.get("inotify_max_queued_events", 65536)),
        }
        for path, required in values.items():
            try:
                current = int(Path(path).read_text().strip())
                if current < required:
                    Path(path).write_text(str(required), encoding="ascii")
            except (OSError, ValueError):
                pass

    def _run_fanotify(self) -> None:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.fanotify_init.argtypes = [ctypes.c_uint, ctypes.c_uint]
        libc.fanotify_init.restype = ctypes.c_int
        libc.fanotify_mark.argtypes = [ctypes.c_int, ctypes.c_uint, ctypes.c_ulonglong, ctypes.c_int, ctypes.c_char_p]
        libc.fanotify_mark.restype = ctypes.c_int
        event_flags = os.O_RDONLY | getattr(os, "O_LARGEFILE", 0) | os.O_CLOEXEC
        fd = libc.fanotify_init(FAN_CLOEXEC | FAN_NONBLOCK, event_flags)
        if fd < 0:
            raise OSError(ctypes.get_errno(), "fanotify_init failed")
        marked = 0
        for path in self.config.get("monitor_paths", []):
            if os.path.isdir(path) and libc.fanotify_mark(fd, FAN_MARK_ADD | FAN_MARK_MOUNT, FAN_CLOSE_WRITE, -100, os.fsencode(path)) == 0:
                marked += 1
        if not marked:
            os.close(fd)
            raise OSError("no monitor mount could be marked")
        self._error = None
        while True:
            ready, _, _ = select.select([fd], [], [], 1.0)
            if not ready:
                continue
            data = os.read(fd, 1024 * 256)
            offset = 0
            while offset + 24 <= len(data):
                event_len, version, _reserved, _metadata_len, mask, event_fd, pid = struct.unpack_from("<IBBHQii", data, offset)
                if event_len < 24:
                    break
                offset += event_len
                if version != FANOTIFY_METADATA_VERSION:
                    raise RuntimeError(f"fanotify metadata version {version}")
                if mask & FAN_Q_OVERFLOW:
                    self._error = "fanotify queue overflow"
                    continue
                if event_fd < 0:
                    continue
                try:
                    self._record_fanotify(os.readlink(f"/proc/self/fd/{event_fd}"), pid)
                except OSError:
                    pass
                finally:
                    os.close(event_fd)

    def _record_fanotify(self, path: str, pid: int) -> None:
        if not os.path.isfile(path):
            return
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        suffix = Path(path).suffix.lower()
        event = {"time": time.time(), "path": self._display_path(path), "kind": "write",
                 "entropy": self._entropy_high(path), "extension_changed": suffix in SUSPICIOUS_SUFFIXES,
                 "bytes": size, "pid": pid}
        with self._lock:
            self.events.append(event)

    def _run_inotify(self) -> None:
        self._error = None
        try:
            self._libc = ctypes.CDLL(None, use_errno=True)
            self._fd = self._libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
            if self._fd < 0:
                raise OSError(ctypes.get_errno(), "inotify_init1 failed")
            for path in self.config.get("monitor_paths", []):
                if os.path.isdir(path):
                    self._add_tree(path)
            while True:
                ready, _, _ = select.select([self._fd], [], [], 1.0)
                if not ready:
                    continue
                data = os.read(self._fd, 1024 * 256)
                offset = 0
                while offset + 16 <= len(data):
                    wd, mask, cookie, length = struct.unpack_from("iIII", data, offset)
                    raw_name = data[offset + 16:offset + 16 + length]
                    offset += 16 + length
                    name = raw_name.split(b"\0", 1)[0].decode("utf-8", "replace")
                    base = self._watches.get(wd)
                    if not base:
                        continue
                    path = os.path.join(base, name) if name else base
                    if mask & IN_ISDIR:
                        if mask & (IN_CREATE | IN_MOVED_TO) and os.path.isdir(path):
                            self._add_tree(path)
                        continue
                    self._record(mask, cookie, path)
        finally:
            if self._fd >= 0:
                os.close(self._fd)
                self._fd = -1

    def _entropy_high(self, path: str) -> bool:
        try:
            if not os.path.isfile(path):
                return False
            with open(path, "rb") as handle:
                sample = handle.read(65536)
            if len(sample) < 4096:
                return False
            counts = [0] * 256
            for byte in sample:
                counts[byte] += 1
            entropy = -sum((count / len(sample)) * math.log2(count / len(sample)) for count in counts if count)
            return entropy >= 7.72
        except OSError:
            return False

    def _display_path(self, path: str) -> str:
        prefix = self.config.get("host_root", "/host").rstrip("/")
        return path[len(prefix):] if path.startswith(prefix + "/") else path

    def _record(self, mask: int, cookie: int, path: str) -> None:
        now = time.time()
        event = {"time": now, "path": self._display_path(path), "kind": "modify", "entropy": False, "extension_changed": False, "bytes": 0}
        if mask & IN_CLOSE_WRITE:
            try:
                event["bytes"] = os.path.getsize(path)
            except OSError:
                pass
            created_at = self._created.get(path)
            if created_at and now - created_at < 120:
                event["kind"] = "create_write"
            else:
                event["kind"] = "write"
                event["entropy"] = self._entropy_high(path)
        elif mask & IN_MOVED_FROM:
            self._renames[cookie] = (now, path, path in self._created)
            return
        elif mask & IN_MOVED_TO:
            previous = self._renames.pop(cookie, None)
            if previous and previous[2]:
                event["kind"] = "move_new"
                self._created[path] = now
            else:
                event["kind"] = "rename"
            if previous and event["kind"] == "rename":
                event["extension_changed"] = Path(previous[1]).suffix.lower() != Path(path).suffix.lower()
        elif mask & IN_DELETE:
            event["kind"] = "delete"
        elif mask & IN_CREATE:
            event["kind"] = "create"
            self._created[path] = now
        if len(self._created) > 5000:
            cutoff = now - 180
            self._created = {name: stamp for name, stamp in self._created.items() if stamp >= cutoff}
        with self._lock:
            self.events.append(event)

    def snapshot(self) -> dict:
        cutoff = time.time() - self.window
        with self._lock:
            while self.events and self.events[0]["time"] < cutoff:
                self.events.popleft()
            events = list(self.events)
        writes = [item for item in events if item["kind"] == "write"]
        renamed = [item for item in events if item["kind"] == "rename"]
        deleted = [item for item in events if item["kind"] == "delete"]
        extension_changed = [item for item in renamed if item["extension_changed"]]
        entropy = [item for item in writes if item["entropy"]]
        write_mib_sec = round(sum(item.get("bytes", 0) for item in writes) / max(1, self.window) / 1024 / 1024, 1)
        score = min(100, len(writes) * 1.1 + len(renamed) * 1.4 + len(deleted) * 1.2 + len(extension_changed) * 4 + len(entropy) * 1.4)
        state = "warning" if score >= 70 else "watch" if score >= 30 else "normal"
        paths = []
        for item in reversed(events):
            if item["path"] not in paths:
                paths.append(item["path"])
            if len(paths) == 3:
                break
        if self._error:
            message = "文件事件监控不可用：" + self._error
        elif state == "warning":
            message = "检测到短时间批量改写、重命名或高熵写入"
        elif state == "watch":
            message = "文件活动明显增加，正在持续观察"
        else:
            message = "文件活动正常"
        source = self._source_for_paths(paths)
        return {
            "timestamp": now_iso(), "state": state, "score": round(score), "window_sec": self.window,
            "files_modified": len(writes), "files_renamed": len(renamed), "files_deleted": len(deleted),
            "extensions_changed": len(extension_changed), "entropy_anomalies": len(entropy), "write_mib_sec": write_mib_sec,
            "source": source,
            "sample_paths": paths, "message": message, "auto_contained": False,
        }

    def _source_for_paths(self, paths: list[str]) -> dict:
        unknown = {"kind": "unknown", "container_name": None, "pid": None, "command": None}
        if not paths:
            return unknown
        try:
            docker = "/var/packages/ContainerManager/target/usr/bin/docker"
            process = host_command(self.config, [docker, "ps", "-q"], timeout=8)
            container_ids = [item for item in process.stdout.splitlines() if item]
            if not container_ids:
                return unknown
            inspected = host_command(self.config, [docker, "inspect", *container_ids], timeout=10)
            containers = json.loads(inspected.stdout)
            for container in containers:
                for mount in container.get("Mounts", []):
                    source_path = str(mount.get("Source", "")).rstrip("/")
                    if source_path not in {"", "/", "/proc", "/sys", "/dev"} and any(path == source_path or path.startswith(source_path + "/") for path in paths):
                        state = container.get("State", {})
                        config = container.get("Config", {})
                        command = " ".join([str(config.get("Entrypoint") or ""), str(config.get("Cmd") or "")]).strip()
                        return {"kind": "docker", "container_name": str(container.get("Name", "")).lstrip("/") or None,
                                "pid": state.get("Pid"), "command": command or None}
        except Exception:
            return unknown
        return unknown
