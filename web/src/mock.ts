import type { ActivityPayload, DisksPayload, SecurityPayload, StatusPayload } from './types'

let cpu = 27
let memory = 38
let simulatedThreat = false
let photoProgress = 62

export function setMockThreat(value: boolean) {
  simulatedThreat = value
}

export function getMockActivity(): ActivityPayload {
  photoProgress = photoProgress >= 96 ? 58 : photoProgress + 1
  return {
    timestamp: new Date().toISOString(),
    privacy_mode: 'status_only',
    active_users: 1,
    activities: [
      {
        id: 'activity-photo-upload',
        username: '演示用户',
        action: 'store_photos',
        action_label: '正在存入照片',
        state: photoProgress >= 92 ? 'finishing' : 'active',
        state_label: photoProgress >= 92 ? '即将完成' : '传输中',
        rate_mib_sec: Number((6.2 + Math.random() * 1.8).toFixed(1)),
        progress_percent: photoProgress,
      },
    ],
  }
}

export function getMockSecurity(): SecurityPayload {
  if (!simulatedThreat) {
    return {
      timestamp: new Date().toISOString(),
      state: 'normal',
      score: 4,
      window_sec: 10,
      files_modified: 3,
      files_renamed: 0,
      files_deleted: 0,
      extensions_changed: 0,
      entropy_anomalies: 0,
      write_mib_sec: 0.4,
      source: { kind: 'unknown', container_name: null, pid: null, command: null },
      sample_paths: [],
      message: '文件活动正常',
      auto_contained: false,
    }
  }

  return {
    timestamp: new Date().toISOString(),
    state: 'warning',
    score: 96,
    window_sec: 10,
    files_modified: 284,
    files_renamed: 117,
    files_deleted: 63,
    extensions_changed: 102,
    entropy_anomalies: 89,
    write_mib_sec: 74.8,
    source: {
      kind: 'docker',
      container_name: 'documents-worker',
      pid: 18427,
      command: 'python /app/worker.py',
    },
    sample_paths: [
      '/volume1/documents/合同/2026报价单.xlsx.locked',
      '/volume1/photos/家庭照片/IMG_2024.jpg.locked',
      '/volume1/backup/财务数据.zip.locked',
    ],
    message: '检测到短时间批量改写和高熵内容写入',
    auto_contained: false,
  }
}

export function getMockStatus(): StatusPayload {
  cpu = Math.min(92, Math.max(8, cpu + (Math.random() - 0.48) * 9))
  memory = Math.min(73, Math.max(32, memory + (Math.random() - 0.5) * 1.5))
  const total = 16 * 1024 ** 3
  const used = Math.round((memory / 100) * total)

  return {
    timestamp: new Date().toISOString(),
    hostname: 'R1-NAS',
    uptime_sec: 18 * 86400 + 7 * 3600 + 42 * 60,
    cpu: {
      usage_percent: Number(cpu.toFixed(1)),
      temperature_c: Math.round(39 + cpu * 0.18),
      load1: Number((cpu / 41).toFixed(2)),
      load5: Number((cpu / 49).toFixed(2)),
      load15: Number((cpu / 57).toFixed(2)),
    },
    memory: {
      total_bytes: total,
      used_bytes: used,
      available_bytes: total - used,
      usage_percent: Number(memory.toFixed(1)),
    },
    storage: null,
  }
}

export function getMockDisks(): DisksPayload {
  return {
    timestamp: new Date().toISOString(),
    disks: [
      {
        device: '/dev/sda',
        model: 'WD Red Plus 4TB',
        state: 'active',
        temperature_c: 38,
        health_passed: true,
        reallocated_sectors: 0,
        power_on_hours: 12345,
        capacity_bytes: 4_000_787_030_016,
        error: null,
      },
      {
        device: '/dev/sdb',
        model: 'Seagate IronWolf 8TB',
        state: 'standby',
        temperature_c: null,
        health_passed: null,
        reallocated_sectors: null,
        power_on_hours: null,
        capacity_bytes: 8_001_563_222_016,
        error: null,
      },
      {
        device: '/dev/sdc',
        model: 'TOSHIBA N300 6TB',
        state: 'active',
        temperature_c: 47,
        health_passed: true,
        reallocated_sectors: 0,
        power_on_hours: 8320,
        capacity_bytes: 6_001_175_126_016,
        error: null,
      },
    ],
  }
}
