<script setup lang="ts">
import networkIcon from '../assets/icons/network.png'
import type { ConnectionState } from '../types'

defineProps<{
  hostname: string
  time: string
  date: string
  state: ConnectionState
  title: string
  canPrevious: boolean
  canNext: boolean
}>()

const emit = defineEmits<{ previous: []; next: [] }>()

function navigate(direction: 'previous' | 'next') {
  if (direction === 'previous') emit('previous')
  else emit('next')
}

const labels: Record<ConnectionState, string> = {
  online: '在线',
  retrying: '重试中',
  offline: '离线',
}
</script>

<template>
  <header class="status-header">
    <div class="host-block">
      <div class="host-line">
        <img :src="networkIcon" alt="" class="header-icon" />
        <strong>{{ hostname }}</strong>
      </div>
      <!-- <span class="connection-label" :class="`is-${state}`">
        <i aria-hidden="true"></i>{{ labels[state] }}
      </span> -->
    </div>
    <div class="page-switcher">
      <button type="button" class="page-arrow previous" :disabled="!canPrevious" aria-label="上一页" @click.stop="navigate('previous')"><i></i></button>
      <Transition name="header-title" mode="out-in">
        <h1 :key="title" class="current-page-title">{{ title }}</h1>
      </Transition>
      <button type="button" class="page-arrow next" :disabled="!canNext" aria-label="下一页" @click.stop="navigate('next')"><i></i></button>
    </div>
    <div class="clock-block">
      <time>{{ time }}</time>
      <span>{{ date }}</span>
    </div>
  </header>
</template>
