<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { fetchActivity, fetchDisks, fetchSecurity, fetchSettings, fetchStatus, saveSettings, setSimulatedOffline, setSimulatedThreat } from './api'
import type { ActivityPayload, ConnectionState, DisksPayload, SecurityPayload, StatusPayload } from './types'
import DisksPage from './components/DisksPage.vue'
import MascotIntro from './components/MascotIntro.vue'
import NameSetup from './components/NameSetup.vue'
import OverviewPage from './components/OverviewPage.vue'
import SecurityAlert from './components/SecurityAlert.vue'
import StatusHeader from './components/StatusHeader.vue'
import SystemPage from './components/SystemPage.vue'

const pages = ['总览', '磁盘状态', '系统状态']
const previewParams = new URLSearchParams(window.location.search)
const requestedPage = Number(previewParams.get('page') ?? 0)
const initialThreat = previewParams.get('threat') === '1'
setSimulatedThreat(initialThreat)
const currentPage = ref(Number.isFinite(requestedPage) ? Math.max(0, Math.min(pages.length - 1, requestedPage)) : 0)
const initialTimestamp = new Date().toISOString()
const status = ref<StatusPayload>({
  timestamp: initialTimestamp,
  hostname: '正在连接 NAS',
  uptime_sec: 0,
  cpu: { usage_percent: 0, temperature_c: null, load1: 0, load5: 0, load15: 0 },
  memory: { total_bytes: 0, used_bytes: 0, available_bytes: 0, usage_percent: 0 },
  storage: null,
})
const diskData = ref<DisksPayload>({ timestamp: initialTimestamp, disks: [] })
const activity = ref<ActivityPayload>({
  timestamp: initialTimestamp,
  privacy_mode: 'status_only',
  active_users: 0,
  activities: [],
})
const connection = ref<ConnectionState>('retrying')
const now = ref(new Date())
const demoOffline = ref(false)
const demoThreat = ref(initialThreat)
const security = ref<SecurityPayload>({
  timestamp: initialTimestamp,
  state: 'normal',
  score: 0,
  window_sec: 10,
  files_modified: 0,
  files_renamed: 0,
  files_deleted: 0,
  extensions_changed: 0,
  entropy_anomalies: 0,
  write_mib_sec: 0,
  source: { kind: 'unknown', container_name: null, pid: null, command: null },
  sample_paths: [],
  message: '正在读取实时监控数据',
  auto_contained: false,
})
const alertAcknowledged = ref(false)
const mascotName = ref('娴宝')
const settingsReady = ref(false)
const settingsConfigured = ref(false)
const editingName = ref(false)
const settingsSaving = ref(false)
const settingsError = ref('')
const showIntro = ref(false)
const introKey = ref(0)
const dragOffset = ref(0)
const isDragging = ref(false)
const viewport = ref<HTMLElement | null>(null)

let statusTimer = 0
let diskTimer = 0
let clockTimer = 0
let securityTimer = 0
let activityTimer = 0
let settingsTimer = 0
let retryFailures = 0
let pointerId: number | null = null
let pointerX = 0
let pointerY = 0
let pointerStartedAt = 0
let gestureDirection: 'pending' | 'horizontal' | 'vertical' = 'pending'
let touchIdentifier: number | null = null
let touchX = 0
let touchY = 0
let touchStartedAt = 0
let touchDirection: 'pending' | 'horizontal' | 'vertical' = 'pending'
let touchPage = 0

const clock = computed(() => new Intl.DateTimeFormat('zh-CN', {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
}).format(now.value))

const dateText = computed(() => new Intl.DateTimeFormat('zh-CN', {
  month: '2-digit',
  day: '2-digit',
  weekday: 'short',
}).format(now.value).replaceAll('/', '.'))

async function updateStatus() {
  try {
    status.value = await fetchStatus()
    retryFailures = 0
    connection.value = 'online'
  } catch {
    retryFailures += 1
    connection.value = retryFailures >= 3 ? 'offline' : 'retrying'
  }
}

async function updateDisks() {
  try {
    diskData.value = await fetchDisks()
  } catch {
    if (connection.value === 'online') connection.value = 'retrying'
  }
}

async function updateActivity() {
  try {
    activity.value = await fetchActivity()
  } catch {
    // 活动接口失败时保留最后一次状态，避免暴露底层错误细节。
  }
}

async function updateSecurity() {
  try {
    security.value = await fetchSecurity()
    if (security.value.state === 'normal') alertAcknowledged.value = false
  } catch {
    // 安全接口短暂不可用不应覆盖现有告警。
  }
}

async function updateSettings() {
  try {
    const payload = await fetchSettings()
    const wasConfigured = settingsConfigured.value
    mascotName.value = payload.mascot_name
    settingsConfigured.value = payload.configured
    if (!wasConfigured && payload.configured) showIntro.value = previewParams.get('intro') !== '0'
  } finally {
    settingsReady.value = true
  }
}

async function setMascotName(name: string) {
  settingsSaving.value = true
  settingsError.value = ''
  try {
    const payload = await saveSettings(name)
    mascotName.value = payload.mascot_name
    settingsConfigured.value = true
    editingName.value = false
    introKey.value += 1
    showIntro.value = true
  } catch {
    settingsError.value = '保存失败，请确认 NAS 服务正常后重试'
  } finally {
    settingsSaving.value = false
  }
}

function goTo(index: number) {
  const target = Math.max(0, Math.min(pages.length - 1, index))
  currentPage.value = target
  const element = viewport.value
  if (element) element.scrollLeft = target * element.clientWidth
}

function onViewportScroll() {
  const element = viewport.value
  if (!element || element.clientWidth === 0) return
  if (touchIdentifier !== null && touchDirection === 'horizontal') return
  const page = Math.max(0, Math.min(pages.length - 1, Math.round(element.scrollLeft / element.clientWidth)))
  if (page !== currentPage.value) currentPage.value = page
}

function onPointerDown(event: PointerEvent) {
  if (event.pointerType === 'mouse' && event.button !== 0) return
  if ((event.target as HTMLElement).closest('button')) return
  pointerId = event.pointerId
  pointerX = event.clientX
  pointerY = event.clientY
  pointerStartedAt = performance.now()
  dragOffset.value = 0
  gestureDirection = 'pending'
}

function onPointerMove(event: PointerEvent) {
  if (pointerId !== event.pointerId) return
  const deltaX = event.clientX - pointerX
  const deltaY = event.clientY - pointerY
  if (gestureDirection === 'pending' && Math.max(Math.abs(deltaX), Math.abs(deltaY)) > 9) {
    gestureDirection = Math.abs(deltaX) > Math.abs(deltaY) + 4 ? 'horizontal' : 'vertical'
    if (gestureDirection === 'horizontal') {
      ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
    }
  }
  if (gestureDirection === 'horizontal') {
    isDragging.value = true
    event.preventDefault()
    const resistance = (currentPage.value === 0 && deltaX > 0) || (currentPage.value === pages.length - 1 && deltaX < 0) ? 0.28 : 0.82
    dragOffset.value = Math.max(-130, Math.min(130, deltaX * resistance))
  }
}

function finishPointer(event: PointerEvent) {
  if (pointerId !== event.pointerId) return
  const deltaX = event.clientX - pointerX
  const deltaY = event.clientY - pointerY
  const elapsed = Math.max(1, performance.now() - pointerStartedAt)
  const velocity = Math.abs(deltaX) / elapsed
  if (gestureDirection === 'horizontal' && Math.abs(deltaY) < 100 && (Math.abs(deltaX) >= 58 || (Math.abs(deltaX) >= 28 && velocity > 0.5))) {
    goTo(currentPage.value + (deltaX < 0 ? 1 : -1))
  }
  dragOffset.value = 0
  isDragging.value = false
  gestureDirection = 'pending'
  pointerId = null
  const target = event.currentTarget as HTMLElement
  if (target.hasPointerCapture(event.pointerId)) target.releasePointerCapture(event.pointerId)
}

function findTrackedTouch(event: TouchEvent) {
  const list = event.touches.length ? event.touches : event.changedTouches
  for (let index = 0; index < list.length; index += 1) {
    const touch = list.item(index)
    if (touch && (touchIdentifier === null || touch.identifier === touchIdentifier)) return touch
  }
  return null
}

function onTouchStart(event: TouchEvent) {
  if (event.touches.length !== 1) return
  if ((event.target as HTMLElement).closest('button')) return
  const touch = event.touches.item(0)
  if (!touch) return
  touchIdentifier = touch.identifier
  touchX = touch.clientX
  touchY = touch.clientY
  touchStartedAt = performance.now()
  touchPage = currentPage.value
  touchDirection = 'pending'
  dragOffset.value = 0
}

function onTouchMove(event: TouchEvent) {
  const touch = findTrackedTouch(event)
  if (!touch) return
  const deltaX = touch.clientX - touchX
  const deltaY = touch.clientY - touchY
  if (touchDirection === 'pending' && Math.max(Math.abs(deltaX), Math.abs(deltaY)) > 8) {
    touchDirection = Math.abs(deltaX) > Math.abs(deltaY) + 3 ? 'horizontal' : 'vertical'
  }
  if (touchDirection !== 'horizontal') return
  event.preventDefault()
  isDragging.value = true
  const element = viewport.value
  if (element) element.scrollLeft = touchPage * element.clientWidth - deltaX
}

function finishTouch(event: TouchEvent) {
  const touch = findTrackedTouch(event)
  if (!touch) return
  const deltaX = touch.clientX - touchX
  const deltaY = touch.clientY - touchY
  const elapsed = Math.max(1, performance.now() - touchStartedAt)
  const velocity = Math.abs(deltaX) / elapsed
  if (touchDirection === 'horizontal' && Math.abs(deltaY) < 120 && (Math.abs(deltaX) >= 45 || (Math.abs(deltaX) >= 22 && velocity > 0.35))) {
    goTo(touchPage + (deltaX < 0 ? 1 : -1))
  } else goTo(touchPage)
  dragOffset.value = 0
  isDragging.value = false
  touchDirection = 'pending'
  touchIdentifier = null
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowRight') goTo(currentPage.value + 1)
  if (event.key === 'ArrowLeft') goTo(currentPage.value - 1)
}

function toggleOfflineDemo() {
  demoOffline.value = !demoOffline.value
  setSimulatedOffline(demoOffline.value)
  if (!demoOffline.value) {
    retryFailures = 0
    void updateStatus()
    void updateDisks()
  }
}

function toggleThreatDemo() {
  demoThreat.value = !demoThreat.value
  setSimulatedThreat(demoThreat.value)
  alertAcknowledged.value = false
  void updateSecurity()
  void updateActivity()
}

function acknowledgeAlert() {
  alertAcknowledged.value = true
}

function replayIntro() {
  introKey.value += 1
  showIntro.value = true
}

onMounted(() => {
  void updateSettings()
  void updateStatus()
  void updateDisks()
  void updateSecurity()
  statusTimer = window.setInterval(updateStatus, 3000)
  diskTimer = window.setInterval(updateDisks, 15000)
  securityTimer = window.setInterval(updateSecurity, 1000)
  activityTimer = window.setInterval(updateActivity, 2200)
  settingsTimer = window.setInterval(() => { if (!settingsConfigured.value) void updateSettings() }, 3000)
  clockTimer = window.setInterval(() => { now.value = new Date() }, 1000)
  window.addEventListener('keydown', onKeydown)
  void nextTick(() => goTo(currentPage.value))
})

onBeforeUnmount(() => {
  window.clearInterval(statusTimer)
  window.clearInterval(diskTimer)
  window.clearInterval(clockTimer)
  window.clearInterval(securityTimer)
  window.clearInterval(activityTimer)
  window.clearInterval(settingsTimer)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <main class="panel-shell">
    <div class="ambient-grid" aria-hidden="true"></div>
    <button class="demo-toggle" type="button" :aria-pressed="demoOffline" @click="toggleOfflineDemo">
      {{ demoOffline ? '恢复连接' : '模拟断线' }}
    </button>
    <button class="threat-demo-toggle" type="button" :aria-pressed="demoThreat" @click="toggleThreatDemo">
      {{ demoThreat ? '解除告警' : '模拟勒索告警' }}
    </button>
    <button v-if="settingsConfigured && !showIntro" class="mascot-return" type="button" :aria-label="`回到${mascotName}的工作台`" @click="replayIntro">
      <span></span><i>{{ mascotName }}</i>
    </button>

    <StatusHeader
      :hostname="status.hostname"
      :time="clock"
      :date="dateText"
      :state="connection"
      :title="pages[currentPage]"
      :can-previous="currentPage > 0"
      :can-next="currentPage < pages.length - 1"
      @previous="goTo(currentPage - 1)"
      @next="goTo(currentPage + 1)"
    />

    <section
      ref="viewport"
      class="viewport"
      aria-live="polite"
      @scroll.passive="onViewportScroll"
      @touchstart.passive="onTouchStart"
      @touchmove="onTouchMove"
      @touchend="finishTouch"
      @touchcancel="finishTouch"
    >
      <div class="pages-track">
        <OverviewPage :status="status" :disks="diskData.disks" />
        <DisksPage :disks="diskData.disks" />
        <SystemPage :status="status" :security="security" :mascot-name="mascotName" @edit-name="editingName = true" />
      </div>
    </section>

    <MascotIntro v-if="showIntro" :key="introKey" :activity="activity" :mascot-name="mascotName" @enter="showIntro = false" />
    <NameSetup
      v-if="settingsReady && (!settingsConfigured || editingName)"
      :initial-name="mascotName"
      :mode="editingName ? 'edit' : 'first-run'"
      :saving="settingsSaving"
      :server-error="settingsError"
      @save="setMascotName"
      @cancel="editingName = false; settingsError = ''"
    />
    <SecurityAlert
      v-if="security.state === 'warning' && !alertAcknowledged"
      :alert="security"
      @acknowledge="acknowledgeAlert"
    />
  </main>
</template>
