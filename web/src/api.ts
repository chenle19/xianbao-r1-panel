import { getMockActivity, getMockDisks, getMockSecurity, getMockStatus, setMockThreat } from './mock'
import type { ActivityPayload, DisksPayload, SecurityPayload, SettingsPayload, StatusPayload } from './types'

// 生产环境必须默认读取 NAS 实时接口。只有明确设置 VITE_USE_MOCK=true
// 时才启用演示数据，避免漏配环境变量后把模拟硬盘当成真实硬盘。
const forceMock = import.meta.env.VITE_USE_MOCK === 'true'
let simulatedOffline = false

export function setSimulatedOffline(value: boolean) {
  simulatedOffline = value
}

export function setSimulatedThreat(value: boolean) {
  setMockThreat(value)
}

async function request<T>(path: string): Promise<T> {
  if (simulatedOffline) throw new Error('模拟连接中断')
  const response = await fetch(path, { cache: 'no-store' })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json() as Promise<T>
}

export function fetchSettings(): Promise<SettingsPayload> {
  return request<SettingsPayload>('/api/settings')
}

export async function saveSettings(mascotName: string): Promise<SettingsPayload> {
  const response = await fetch('/api/settings', {
    method: 'POST',
    cache: 'no-store',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mascot_name: mascotName }),
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json() as Promise<SettingsPayload>
}

export async function fetchStatus(): Promise<StatusPayload> {
  if (forceMock) return getMockStatus()
  return request<StatusPayload>('/api/status')
}

export async function fetchDisks(): Promise<DisksPayload> {
  if (forceMock) return getMockDisks()
  return request<DisksPayload>('/api/disks')
}

export async function fetchActivity(): Promise<ActivityPayload> {
  if (forceMock) return getMockActivity()
  return request<ActivityPayload>('/api/activity')
}

export async function fetchSecurity(): Promise<SecurityPayload> {
  if (forceMock) return getMockSecurity()
  return request<SecurityPayload>('/api/security')
}
