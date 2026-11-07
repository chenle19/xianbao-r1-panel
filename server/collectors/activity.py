from __future__ import annotations

import json
from pathlib import PurePosixPath

from .common import host_command, now_iso


PHOTO = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".raw", ".dng"}
MEDIA = {".mp4", ".mkv", ".mov", ".avi", ".mp3", ".flac", ".wav"}
BACKUP = {".bak", ".backup", ".dss", ".hbk", ".tar", ".zip", ".7z"}


def _classify(path: str | None) -> tuple[str, str]:
    suffix = PurePosixPath(path or "").suffix.lower()
    if suffix in PHOTO:
        return "store_photos", "正在存入照片"
    if suffix in MEDIA:
        return "read_media", "正在使用媒体文件"
    if suffix in BACKUP:
        return "backup", "正在备份数据"
    if path:
        return "sync_files", "正在同步文件"
    return "access_nas", "已连接 NAS"


def collect_activity(config: dict) -> dict:
    command = [config.get("smbstatus_path"), "--json"]
    try:
        process = host_command(config, command, timeout=12)
        data = json.loads(process.stdout)
    except Exception:
        data = {"sessions": {}, "open_files": {}}

    sessions = data.get("sessions") or {}
    session_users: dict[str, str] = {}
    for item in sessions.values() if isinstance(sessions, dict) else sessions:
        if not isinstance(item, dict):
            continue
        username = item.get("username") or item.get("user")
        session_id = str(item.get("session_id", ""))
        if username:
            session_users[session_id] = str(username)

    by_user: dict[str, tuple[str, str]] = {}
    open_files = data.get("open_files") or {}
    for item in open_files.values() if isinstance(open_files, dict) else open_files:
        if not isinstance(item, dict):
            continue
        username = item.get("username") or session_users.get(str(item.get("session_id", "")))
        if not username:
            continue
        # 路径只用于瞬时分类，不写日志、不进入 API。
        private_path = item.get("filename") or item.get("path") or item.get("name")
        by_user[str(username)] = _classify(str(private_path) if private_path else None)

    for username in session_users.values():
        by_user.setdefault(username, ("access_nas", "已连接 NAS"))

    activities = []
    for index, (username, (action, label)) in enumerate(sorted(by_user.items())):
        activities.append({
            "id": f"smb-{index}",
            "username": username,
            "action": action,
            "action_label": label,
            "state": "active",
            "state_label": "使用中",
            "rate_mib_sec": None,
            "progress_percent": None,
        })
    return {
        "timestamp": now_iso(),
        "privacy_mode": "status_only",
        "active_users": len(activities),
        "activities": activities[:6],
    }
