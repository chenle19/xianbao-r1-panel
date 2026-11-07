<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import girlSprite from '../assets/mascot/girl-sprite.webp'
import type { ActivityPayload } from '../types'

const emit = defineEmits<{ enter: [] }>()
defineProps<{ activity: ActivityPayload; mascotName: string }>()
const phase = ref<'typing' | 'turned' | 'zooming'>('typing')
let turnTimer = 0
let enterTimer = 0

function openPanel() {
  if (phase.value !== 'typing') return
  phase.value = 'turned'
  turnTimer = window.setTimeout(() => {
    phase.value = 'zooming'
    enterTimer = window.setTimeout(() => emit('enter'), 720)
  }, 760)
}

onBeforeUnmount(() => {
  window.clearTimeout(turnTimer)
  window.clearTimeout(enterTimer)
})
</script>

<template>
  <section class="mascot-intro" :class="`phase-${phase}`">
    <div class="intro-stars" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
    <div class="intro-copy">
      <span>{{ phase === 'typing' ? 'NAS 巡检中' : phase === 'turned' ? '发现你啦' : '正在打开面板' }}</span>
      <h1>{{ phase === 'typing' ? `${mascotName}正在认真工作` : phase === 'turned' ? '要一起看看吗？' : '屏幕准备好了' }}</h1>
      <p>{{ phase === 'typing' ? '轻点一下她的电脑' : phase === 'turned' ? '所有状态都在这块屏幕里' : '稍等一下下' }}</p>
    </div>

    <div v-if="phase === 'typing'" class="user-activity" aria-live="polite">
      <div class="activity-heading">
        <span><i aria-hidden="true"></i>实时使用状态</span>
        <small>仅状态 · 不读取内容</small>
      </div>
      <div v-if="activity.activities.length" class="activity-row">
        <div class="activity-avatar" aria-hidden="true">{{ activity.activities[0].username.slice(0, 1) }}</div>
        <div class="activity-copy">
          <strong>{{ activity.activities[0].username }}</strong>
          <span>{{ activity.activities[0].action_label }}</span>
        </div>
        <div class="activity-rate">
          <b>{{ activity.activities[0].state_label }}</b>
          <span v-if="activity.activities[0].rate_mib_sec !== null">{{ activity.activities[0].rate_mib_sec }} MiB/s</span>
        </div>
      </div>
      <div v-else class="activity-empty">当前没有用户传输文件</div>
      <div v-if="activity.activities[0]?.progress_percent != null" class="activity-progress" aria-hidden="true">
        <i :style="{ transform: 'scaleX(' + activity.activities[0].progress_percent / 100 + ')' }"></i>
      </div>
    </div>

    <button class="mascot-stage" type="button" aria-label="打开 NAS 监控面板" @click="openPanel">
      <div class="sprite-window">
        <img :src="girlSprite" alt="Q版小女孩坐在电脑前检查 NAS" />
      </div>
      <div v-if="phase !== 'typing'" class="laptop-preview" aria-hidden="true">
        <span>CPU</span><b>27%</b><i></i>
      </div>
      <div v-if="phase === 'typing'" class="typing-bubble" aria-hidden="true"><i></i><i></i><i></i></div>
    </button>

    <div class="tap-hint" :class="{ hidden: phase !== 'typing' }">
      <i aria-hidden="true"></i><span>点击进入</span>
    </div>
    <div v-if="phase === 'zooming'" class="monitor-takeover" aria-hidden="true"></div>
  </section>
</template>
