<script setup lang="ts">
import { computed } from 'vue'
import cpuIcon from '../assets/icons/cpu.png'
import diskIcon from '../assets/icons/disk.png'
import memoryIcon from '../assets/icons/memory.png'
import systemIcon from '../assets/icons/system.png'
import type { DiskInfo, StatusPayload } from '../types'

const props = defineProps<{ status: StatusPayload; disks: DiskInfo[] }>()

const usedGb = computed(() => props.status.memory.used_bytes / 1024 ** 3)
const availableGb = computed(() => props.status.memory.available_bytes / 1024 ** 3)
const totalGb = computed(() => props.status.memory.total_bytes / 1024 ** 3)
const activeDisks = computed(() => props.disks.filter((disk) => disk.state === 'active').length)
const standbyDisks = computed(() => props.disks.filter((disk) => disk.state === 'standby').length)
const hottestDisk = computed(() => {
  const values = props.disks.map((disk) => disk.temperature_c).filter((value): value is number => value !== null)
  return values.length ? Math.max(...values) : null
})

function compactUptime(totalSeconds: number) {
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  return `${days}天 ${hours}小时`
}

function tempTone(value: number | null) {
  if (value === null) return 'neutral'
  if (value > 55) return 'danger'
  if (value > 50) return 'warning'
  return 'normal'
}
</script>

<template>
  <div class="page overview-page">
    <section class="overview-cpu">
      <div class="overview-card-head">
        <div><span>CPU</span><strong>处理器状态</strong></div>
        <img :src="cpuIcon" alt="" />
      </div>
      <div class="cpu-primary">
        <div class="overview-percent"><b>{{ Math.round(status.cpu.usage_percent) }}</b><span>%</span><small>使用率</small></div>
        <div class="cpu-temperature" :class="`temp-${tempTone(status.cpu.temperature_c)}`">
          <span>核心温度</span>
          <strong>{{ status.cpu.temperature_c ?? '--' }}<small v-if="status.cpu.temperature_c !== null">°C</small></strong>
          <em>{{ status.cpu.temperature_c !== null && status.cpu.temperature_c > 50 ? '温度偏高' : '温度正常' }}</em>
        </div>
      </div>
      <div class="cpu-meter"><i :style="{ transform: `scaleX(${Math.max(.02, status.cpu.usage_percent / 100)})` }"></i></div>
      <!-- <div class="load-grid">
        <div><span>1 分钟</span><b>{{ status.cpu.load1.toFixed(2) }}</b><i :style="{ transform: `scaleX(${Math.min(1, status.cpu.load1 / 4)})` }"></i></div>
        <div><span>5 分钟</span><b>{{ status.cpu.load5.toFixed(2) }}</b><i :style="{ transform: `scaleX(${Math.min(1, status.cpu.load5 / 4)})` }"></i></div>
        <div><span>15 分钟</span><b>{{ status.cpu.load15.toFixed(2) }}</b><i :style="{ transform: `scaleX(${Math.min(1, status.cpu.load15 / 4)})` }"></i></div>
      </div> -->
    </section>

    <section class="overview-memory">
      <div class="overview-card-head">
        <div><span>MEMORY</span><strong>内存状态</strong></div>
        <img :src="memoryIcon" alt="" />
      </div>
      <div class="memory-content">
        <div class="overview-percent amber"><b>{{ Math.round(status.memory.usage_percent) }}</b><span>%</span><small>已占用</small></div>
        <div class="flex right-memory">
          <div><dt>用</dt><dd>{{ usedGb.toFixed(1) }} <span>GB</span></dd></div>
          <div><dt>未</dt><dd>{{ availableGb.toFixed(1) }} <span>GB</span></dd></div>
          <div><dt>总</dt><dd>{{ totalGb.toFixed(0) }} <span>GB</span></dd></div>
        </div>
      </div>
      <div class="memory-meter"><i :style="{ transform: `scaleX(${Math.max(.02, status.memory.usage_percent / 100)})` }"></i><span :style="{ left: `${status.memory.usage_percent}%` }"></span></div>
    </section>

    <section class="overview-summary">
      <div class="uptime-summary">
        <img :src="systemIcon" alt="" />
        <div><span>持续运行</span><strong>{{ compactUptime(status.uptime_sec) }}</strong></div>
      </div>
      <div class="disk-overview">
        <div class="disk-overview-head"><img :src="diskIcon" alt="" /><span>盘位概况</span><small>{{ activeDisks }} 运行 · {{ standbyDisks }} 休眠</small></div>
        <div class="mini-bays">
          <div v-for="(disk, index) in disks.slice(0, 3)" :key="disk.device" class="mini-bay" :class="`state-${disk.state}`">
            <b>{{ index + 1 }}</b><span>{{ disk.state === 'standby' ? '休眠' : disk.temperature_c === null ? '--' : `${disk.temperature_c}°` }}</span>
          </div>
        </div>
        <small>最高盘温 {{ hottestDisk ?? '--' }}°C</small>
      </div>
    </section>
  </div>
</template>
