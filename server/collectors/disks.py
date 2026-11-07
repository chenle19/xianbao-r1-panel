from __future__ import annotations

import glob
import json
import re

from .common import host_command, host_path, now_iso


def _attribute(attributes: list[dict], attribute_id: int) -> int | None:
    for item in attributes:
        if item.get("id") == attribute_id:
            raw = item.get("raw", {}).get("value")
            return int(raw) if isinstance(raw, (int, float)) else None
    return None


def parse_synodisk_info(stdout: str) -> dict:
    def match(pattern: str):
        found = re.search(pattern, stdout, re.MULTILINE | re.IGNORECASE)
        return found.group(1).strip() if found else None

    model = match(r"^>> Disk model:\s*(.+)$")
    capacity_gib = match(r"^>> Total capacity:\s*([\d.]+)\s*GB")
    temperature = match(r"^>> Tempeture:\s*(-?[\d.]+)\s*C")
    return {
        "model": model,
        "capacity_bytes": int(float(capacity_gib) * 1024 ** 3) if capacity_gib else None,
        "temperature_c": int(round(float(temperature))) if temperature else None,
    }


def parse_smartctl(device: str, stdout: str, stderr: str, returncode: int) -> dict:
    combined = (stdout + "\n" + stderr).strip()
    standby = "STANDBY" in combined.upper() and not stdout.lstrip().startswith("{")
    if standby:
        return {"device": device, "state": "standby", "temperature_c": None, "health_passed": None,
                "reallocated_sectors": None, "power_on_hours": None, "error": None}
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        def match(pattern: str):
            found = re.search(pattern, combined, re.MULTILINE | re.IGNORECASE)
            return found.group(1).strip() if found else None
        model = match(r"^(?:Device Model|Model Number):\s*(.+)$")
        if not model:
            vendor = match(r"^Vendor:\s*(.+)$")
            product = match(r"^Product:\s*(.+)$")
            model = " ".join(part for part in (vendor, product) if part) or None
        serial = match(r"^Serial (?:Number|number):\s*(.+)$")
        capacity_raw = match(r"^User Capacity:\s*([\d,]+) bytes")
        health_raw = match(r"^(?:SMART overall-health self-assessment test result|SMART Health Status):\s*(.+)$")
        temp_raw = match(r"^\s*194\s+Temperature_Celsius\s+.*?\s-\s+(-?\d+)") or match(r"^Current Drive Temperature:\s*(\d+)")
        realloc_raw = match(r"^\s*5\s+Reallocated_Sector_Ct\s+.*?\s-\s+(\d+)")
        hours_raw = match(r"^\s*9\s+Power_On_Hours\s+.*?\s-\s+(\d+)")
        if model or health_raw:
            temperature = int(temp_raw) if temp_raw and int(temp_raw) > 0 else None
            return {"device": device, "model": model, "serial": serial, "state": "active",
                    "temperature_c": temperature,
                    "health_passed": ("PASSED" in health_raw.upper() or "OK" in health_raw.upper()) if health_raw else None,
                    "reallocated_sectors": int(realloc_raw) if realloc_raw else None,
                    "power_on_hours": int(hours_raw) if hours_raw else None,
                    "capacity_bytes": int(capacity_raw.replace(",", "")) if capacity_raw else None, "error": None}
        return {"device": device, "state": "error", "temperature_c": None, "health_passed": None,
                "reallocated_sectors": None, "power_on_hours": None, "error": combined[-240:] or "smartctl no output"}

    messages = " ".join(str(item.get("string", "")) for item in data.get("smartctl", {}).get("messages", []))
    if "STANDBY" in messages.upper() or data.get("power_mode", "").lower() == "standby":
        return {"device": device, "model": data.get("model_name"), "state": "standby", "temperature_c": None,
                "health_passed": None, "reallocated_sectors": None, "power_on_hours": None, "error": None}

    attributes = data.get("ata_smart_attributes", {}).get("table", [])
    temp = data.get("temperature", {}).get("current")
    if temp is None:
        temp = _attribute(attributes, 194) or _attribute(attributes, 190)
    capacity = data.get("user_capacity", {}).get("bytes")
    health = data.get("smart_status", {}).get("passed")
    error = None
    if returncode and not data:
        error = combined[-240:]
    return {
        "device": device,
        "model": data.get("model_name") or data.get("scsi_model_name"),
        "serial": data.get("serial_number"),
        "state": "active" if error is None else "error",
        "temperature_c": int(temp) if isinstance(temp, (int, float)) else None,
        "health_passed": health if isinstance(health, bool) else None,
        "reallocated_sectors": _attribute(attributes, 5),
        "power_on_hours": data.get("power_on_time", {}).get("hours") or _attribute(attributes, 9),
        "capacity_bytes": int(capacity) if isinstance(capacity, (int, float)) else None,
        "error": error,
    }


def discover_disks(config: dict) -> list[str]:
    base = str(host_path(config, "/dev"))
    mdstat = host_path(config, "/proc/mdstat")
    devices: set[str] = set()
    if mdstat.is_file():
        members = re.findall(r"\b(sata\d+)p3\[", mdstat.read_text(encoding="utf-8", errors="replace"))
        devices.update(f"/dev/{name}" for name in members)
    # mdstat 只列出阵列成员，系统盘、缓存盘或尚未加入阵列的盘也必须显示。
    # 因此 RAID 成员仅作为补充，最终仍枚举所有真实块设备。
    for pattern in (base + "/sata[0-9]*", base + "/sd[a-z]", base + "/nvme[0-9]n[0-9]"):
        for path in glob.glob(pattern):
            name = path.replace(base, "/dev")
            if re.search(r"p\d+$", name):
                continue
            devices.add(name)
    return sorted(devices, key=lambda value: [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", value)])


def collect_disks(config: dict) -> dict:
    result = []
    for device in discover_disks(config):
        args = [config.get("smartctl_path", "/usr/bin/smartctl")]
        if config.get("avoid_spinup", True):
            args += ["-n", "standby"]
        args += ["-i", "-H", "-A", device]
        try:
            process = host_command(config, args, timeout=25)
            disk = parse_smartctl(device, process.stdout, process.stderr, process.returncode)
            # 群晖启动盘可能不开放 SMART，但 DSM 仍能提供真实型号、容量与温度。
            # 使用 synodisk 补齐缺失字段，避免把正常系统盘误报为故障盘。
            if disk.get("state") == "error" or not disk.get("model") or disk.get("temperature_c") is None:
                try:
                    synodisk = host_command(config, ["/usr/syno/bin/synodisk", "--info", device], timeout=10)
                    metadata = parse_synodisk_info(synodisk.stdout + "\n" + synodisk.stderr)
                    for key in ("model", "capacity_bytes", "temperature_c"):
                        if metadata.get(key) is not None:
                            disk[key] = metadata[key]
                    if metadata.get("model"):
                        disk["state"] = "active"
                        disk["error"] = None
                except Exception:
                    pass
            result.append(disk)
        except Exception as exc:
            result.append({"device": device, "state": "error", "temperature_c": None, "health_passed": None,
                           "reallocated_sectors": None, "power_on_hours": None, "error": str(exc)[:240]})
    return {"timestamp": now_iso(), "disks": result}
