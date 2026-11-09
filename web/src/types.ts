export type ConnectionState = 'online' | 'retrying' | 'offline'
export type DiskState = 'active' | 'standby' | 'error'

export interface StatusPayload {
  timestamp: string
  hostname: string
  uptime_sec: number
  cpu: {
    usage_percent: number
    temperature_c: number | null
    load1: number
    load5: number
    load15: number
  }
  memory: {
    total_bytes: number
    used_bytes: number
    available_bytes: number
    usage_percent: number
  }
  storage: null | Record<string, unknown>
}

export interface DiskInfo {
  device: string
  model?: string
  serial?: string
  state: DiskState
  temperature_c: number | null
  health_passed: boolean | null
  reallocated_sectors: number | null
  power_on_hours: number | null
  capacity_bytes?: number
  error: string | null
}

export interface DisksPayload {
  timestamp: string
  disks: DiskInfo[]
}

export interface SettingsPayload {
  mascot_name: string
  configured: boolean
}

export type ControlAction = 'screen_off' | 'screen_off_boot' | 'shutdown'

export interface ControlResponse {
  ok: boolean
  action: ControlAction
  state: 'queued'
}

export interface ControlState {
  state: string
  available: boolean
}

export type ActivityState = 'active' | 'finishing' | 'completed'

export interface UserActivity {
  id: string
  username: string
  action: 'store_photos' | 'sync_files' | 'backup' | 'read_media' | 'access_nas'
  action_label: string
  state: ActivityState
  state_label: string
  rate_mib_sec: number | null
  progress_percent: number | null
}

export interface ActivityPayload {
  timestamp: string
  privacy_mode: 'status_only'
  active_users: number
  activities: UserActivity[]
}

export type SecurityState = 'normal' | 'watch' | 'warning'

export interface SecurityPayload {
  timestamp: string
  state: SecurityState
  score: number
  window_sec: number
  files_modified: number
  files_renamed: number
  files_deleted: number
  extensions_changed: number
  entropy_anomalies: number
  write_mib_sec: number
  source: {
    kind: 'docker' | 'process' | 'unknown'
    container_name: string | null
    pid: number | null
    command: string | null
  }
  sample_paths: string[]
  message: string
  auto_contained: boolean
}
