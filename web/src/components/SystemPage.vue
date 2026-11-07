<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchControlState, sendControl } from '../api'
import systemIcon from '../assets/icons/system.png'
import { formatUptime } from '../format'
import securitySprite from '../assets/icons/disk-details-sprite.webp'
import type { SecurityPayload, StatusPayload } from '../types'

defineProps<{ status: StatusPayload; security: SecurityPayload; mascotName: string }>()
defineEmits<{ editName: [] }>()

const shutdownOpen = ref(false)
const actionState = ref<'idle' | 'screen' | 'shutdown' | 'error'>('idle')
const actionError = ref('')
const controlsAvailable = ref(false)

onMounted(async () => {
  try { controlsAvailable.value = (await fetchControlState()).available } catch { controlsAvailable.value = false }
})

async function screenOff() {
  if (actionState.value !== 'idle') return
  actionState.value = 'screen'
  actionError.value = ''
  try {
    await sendControl('screen_off')
  } catch {
    actionState.value = 'error'
    actionError.value = '关闭屏幕失败，请稍后重试'
  }
}

async function shutdown() {
  if (actionState.value === 'shutdown') return
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
        <button type="button" class="device-control screen-control" :disabled="actionState !== 'idle'" @click="screenOff">
          <span class="control-icon screen-icon"><i></i></span>
          <strong>{{ actionState === 'screen' ? '正在关闭' : '关闭屏幕' }}</strong>
          <small>双击屏幕唤醒</small>
        </button>
        <button type="button" class="device-control power-control" :disabled="actionState === 'shutdown'" @click="shutdownOpen = true">
          <span class="control-icon power-icon"><i></i></span>
          <strong>安全关机</strong>
          <small>由 DSM 正常关闭</small>
        </button>
      </div>
      <p v-if="actionError" class="control-error">{{ actionError }}</p>
    </section>
    <section v-else class="device-controls-unavailable">设备控制仅在 R1 内置屏幕开放</section>

    <div class="version-row">
      <span>面板版本</span><b>0.4.0 · 海康威视 R1 专用版</b>
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
  </div>
</template>
