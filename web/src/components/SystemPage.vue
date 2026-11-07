<script setup lang="ts">
import systemIcon from '../assets/icons/system.png'
import { formatUptime } from '../format'
import securitySprite from '../assets/icons/disk-details-sprite.webp'
import type { SecurityPayload, StatusPayload } from '../types'

defineProps<{ status: StatusPayload; security: SecurityPayload; mascotName: string }>()
defineEmits<{ editName: [] }>()
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

    <div class="version-row">
      <span>面板版本</span><b>0.3.0 · 海康威视 R1 专用版</b>
    </div>
  </div>
</template>
