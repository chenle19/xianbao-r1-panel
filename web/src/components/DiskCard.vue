<script setup lang="ts">
import diskIcon from '../assets/icons/disk.png'
import sleepIcon from '../assets/icons/sleep.png'
import detailSprite from '../assets/icons/disk-details-sprite.webp'
import { formatBytes, formatHours } from '../format'
import type { DiskInfo } from '../types'

defineProps<{ disk: DiskInfo; slot: number }>()

function stateLabel(state: DiskInfo['state']) {
  return { active: '运行中', standby: '休眠', error: '异常' }[state]
}

function tempClass(temp: number | null) {
  if (temp === null) return ''
  if (temp > 55) return 'danger'
  if (temp > 50) return 'warning'
  return ''
}
</script>

<template>
  <article class="disk-card" :class="`state-${disk.state}`">
    <div class="disk-card-head">
      <div class="bay-badge"><span>{{ slot }}</span><small>盘位</small></div>
      <div>
        <strong>硬盘 {{ slot }}</strong>
        <span>{{ disk.model ?? '未知型号' }}</span>
        <!-- <small class="disk-identity">{{ disk.device }}<template v-if="disk.serial"> · SN {{ disk.serial }}</template></small> -->
      </div>
      <div class="disk-head-status">
        <img :src="disk.state === 'standby' ? sleepIcon : diskIcon" alt="" />
        <em>{{ stateLabel(disk.state) }}</em>
      </div>
    </div>

    <template v-if="disk.state !== 'error'">
      <div class="disk-temperature" :class="tempClass(disk.temperature_c)">
        <span>温度</span>
        <strong>{{ disk.temperature_c ?? '--' }}<small v-if="disk.temperature_c !== null">°C</small></strong>
      </div>
      <dl class="disk-facts">
        <div><span class="sprite-icon icon-health" :style="{ backgroundImage: `url(${detailSprite})` }"></span><dt>健康</dt><dd>{{ disk.health_passed === null ? '--' : disk.health_passed ? '良好' : '失败' }}</dd></div>
        <div><span class="sprite-icon icon-warning" :style="{ backgroundImage: `url(${detailSprite})` }"></span><dt id="hd" class="hd">坏道</dt><dd>{{ disk.reallocated_sectors ?? '--' }}</dd></div>
        <div><span class="sprite-icon icon-hours" :style="{ backgroundImage: `url(${detailSprite})` }"></span><dt>通电</dt><dd>{{ formatHours(disk.power_on_hours) }}</dd></div>
        <div><span class="sprite-icon icon-capacity" :style="{ backgroundImage: `url(${detailSprite})` }"></span><dt>容量</dt><dd>{{ disk.capacity_bytes ? formatBytes(disk.capacity_bytes) : '--' }}</dd></div>
      </dl>
    </template>
    <p v-else class="disk-error">{{ disk.error || '无法读取 SMART 信息' }}</p>
  </article>
</template>
