<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchControlState, sendControl } from '../api'
import systemIcon from '../assets/icons/system.png'
import { formatUptime } from '../format'
import securitySprite from '../assets/icons/disk-details-sprite.webp'
import type { SecurityPayload, StatusPayload } from '../types'

defineProps<{ status: StatusPayload; security: SecurityPayload; mascotName: string }>()
defineEmits<{ editName: [] }>()

const shutdownOpen = ref(false)
const hardScreenOpen = ref(false)
const actionState = ref<'idle' | 'screen' | 'hard-screen' | 'shutdown' | 'error'>('idle')
const actionError = ref('')
const controlsAvailable = ref(false)
const actionBusy = computed(() => ['screen', 'hard-screen', 'shutdown'].includes(actionState.value))

onMounted(async () => {
  try { controlsAvailable.value = (await fetchControlState()).available } catch { controlsAvailable.value = false }
})

async function screenOff() {
  if (actionBusy.value) return
  actionState.value = 'screen'
  actionError.value = ''
  try {
    await sendControl('screen_off')
  } catch {
    actionState.value = 'error'
    actionError.value = '关闭屏幕失败，请稍后重试'
  }
}

async function screenOffUntilReboot() {
  if (actionBusy.value) return
  actionState.value = 'hard-screen'
  actionError.value = ''
  try {
    await sendControl('screen_off_boot')
    hardScreenOpen.value = false
  } catch {
    actionState.value = 'error'
    actionError.value = '彻底熄屏失败，屏幕将保持可用'
  }
}

async function shutdown() {
  if (actionBusy.value) return
  actionState.value = 'shutdown'
  actionError.value = ''
  try {
    await sendControl('shutdown')
    shutdownOpen.value = false
  } catch {
    actionState.value = 'error'
    actionError.value = '安全关机请求失败'
  }
}
</script>

<template>
  <div class="page system-page">
    <div class="system-hero">
      <img :src="systemIcon" alt="" />
      <span>稳定运行</span>
      <strong>{{ formatUptime(status.uptime_sec) }}</strong>
    </div>

    <section class="system-section">
      <h2>负载趋势</h2>
      <div class="load-columns">
        <div><b>{{ status.cpu.load1.toFixed(2) }}</b><span>1 分钟</span></div>
        <div><b>{{ status.cpu.load5.toFixed(2) }}</b><span>5 分钟</span></div>
        <div><b>{{ status.cpu.load15.toFixed(2) }}</b><span>15 分钟</span></div>
      </div>
    </section>

    <section class="system-section storage-placeholder">
      <div>
        <h2>存储池 / RAID</h2>
        <p>后端接入后显示阵列与容量信息</p>
      </div>
      <strong>N/A</strong>
    </section>

    <section class="security-status-card" :class="`state-${security.state}`">
      <span class="security-shield" :style="{ backgroundImage: `url(${securitySprite})` }"></span>
      <div>
        <h2>文件行为防护</h2>
        <p>{{ security.message }}</p>
      </div>
      <strong>{{ security.state === 'normal' ? '正常' : security.state === 'watch' ? '观察' : '告警' }}</strong>
      <small>评分 {{ security.score }} · {{ security.window_sec }} 秒内 {{ security.files_modified }} 次改写</small>
    </section>

    <button class="mascot-name-setting" type="button" @click="$emit('editName')">
      <span>小女孩名称</span><strong>{{ mascotName }}</strong><small>点击修改</small>
    </button>

    <section v-if="controlsAvailable" class="device-controls">
      <h2>设备控制</h2>
      <div class="device-control-grid">
        <button type="button" class="device-control screen-control" :disabled="actionBusy" @click="screenOff">
          <span class="control-icon screen-icon"><i></i></span>
          <strong>{{ actionState === 'screen' ? '正在关闭' : '关闭屏幕' }}</strong>
          <small>双击唤醒 · 背光保留</small>
        </button>
        <button type="button" class="device-control power-control" :disabled="actionBusy" @click="shutdownOpen = true">
          <span class="control-icon power-icon"><i></i></span>
          <strong>安全关机</strong>
          <small>由 DSM 正常关闭</small>
        </button>
        <button type="button" class="device-control hard-screen-control" :disabled="actionBusy" @click="hardScreenOpen = true">
          <span class="control-icon hard-screen-icon"><i></i></span>
          <span class="hard-screen-copy">
            <strong>本次开机彻底熄屏</strong>
            <small>触摸无法唤醒 · 重启 NAS 恢复</small>
          </span>
        </button>
      </div>
      <p v-if="actionError" class="control-error">{{ actionError }}</p>
    </section>
    <section v-else class="device-controls-unavailable">设备控制仅在 R1 内置屏幕开放</section>

    <div class="version-row">
      <span>面板版本</span><b>0.4.1 · 海康威视 R1 专用版</b>
    </div>

    <div v-if="shutdownOpen" class="shutdown-sheet" role="dialog" aria-modal="true" aria-labelledby="shutdown-title">
      <div class="shutdown-dialog">
        <span class="shutdown-symbol"><i></i></span>
        <h2 id="shutdown-title">确认关闭 NAS？</h2>
        <p>系统会像群晖关机一样，先安全停止服务并卸载磁盘。关机完成前不要断电。</p>
        <button class="shutdown-confirm" type="button" :disabled="actionState === 'shutdown'" @click="shutdown">{{ actionState === 'shutdown' ? '正在提交关机' : '安全关闭 NAS' }}</button>
        <button class="shutdown-cancel" type="button" @click="shutdownOpen = false">取消</button>
      </div>
    </div>

    <div v-if="hardScreenOpen" class="shutdown-sheet hard-screen-sheet" role="dialog" aria-modal="true" aria-labelledby="hard-screen-title">
      <div class="shutdown-dialog hard-screen-dialog">
        <span class="shutdown-symbol hard-screen-symbol"><i></i></span>
        <h2 id="hard-screen-title">本次开机彻底熄屏？</h2>
        <p>屏幕背光会真正关闭，触摸和双击都无法唤醒，只能重启 NAS 恢复。</p>
        <p class="hard-screen-warning">此模式会暂停 R1 的显卡驱动，视频硬件转码可能暂时不可用；存储与网络服务仍会继续运行。</p>
        <button class="shutdown-confirm hard-screen-confirm" type="button" :disabled="actionState === 'hard-screen'" @click="screenOffUntilReboot">{{ actionState === 'hard-screen' ? '正在彻底熄屏' : '确认彻底熄屏' }}</button>
        <button class="shutdown-cancel" type="button" :disabled="actionState === 'hard-screen'" @click="hardScreenOpen = false">取消</button>
      </div>
    </div>
  </div>
</template>
