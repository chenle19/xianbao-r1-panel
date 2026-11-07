<script setup lang="ts">
import type { DiskInfo } from '../types'
import DiskCard from './DiskCard.vue'

defineProps<{ disks: DiskInfo[] }>()

function physicalSlot(disk: DiskInfo, index: number) {
  const match = disk.device.match(/\/dev\/sata(\d+)$/i)
  return match ? Number(match[1]) : index + 1
}
</script>

<template>
  <div class="page disks-page">
    <div v-if="disks.length" class="disk-list">
      <DiskCard v-for="(disk, index) in disks" :key="disk.device" :disk="disk" :slot="physicalSlot(disk, index)" />
    </div>
    <div v-else class="empty-state">尚未发现磁盘</div>
  </div>
</template>
