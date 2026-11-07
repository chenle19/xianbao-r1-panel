export function formatBytes(value: number): string {
  if (!Number.isFinite(value)) return '--'
  if (value >= 1024 ** 5) return `${(value / 1024 ** 5).toFixed(1)} PB`
  if (value >= 1024 ** 4) return `${(value / 1024 ** 4).toFixed(1)} TB`
  if (value >= 1024 ** 3) return `${(value / 1024 ** 3).toFixed(1)} GB`
  return `${Math.round(value)} B`
}

export function formatUptime(totalSeconds: number): string {
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  return `${days}天 ${hours}时 ${minutes}分`
}

export function formatHours(hours: number | null): string {
  if (hours === null) return '--'
  if (hours > 8760) return `${(hours / 8760).toFixed(1)} 年`
  return `${hours.toLocaleString()} 小时`
}
