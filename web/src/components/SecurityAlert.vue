<script setup lang="ts">
import type { SecurityPayload } from '../types'

defineProps<{ alert: SecurityPayload }>()
defineEmits<{ acknowledge: [] }>()
</script>

<template>
  <section class="security-alert" role="alertdialog" aria-modal="true" aria-labelledby="security-title">
    <div class="warning-pulse" aria-hidden="true"><i>!</i></div>
    <span class="warning-label">WARNING · 疑似勒索行为</span>
    <h1 id="security-title">检测到批量文件改写</h1>
    <p>{{ alert.message }}</p>

    <div class="risk-score"><span>风险评分</span><strong>{{ alert.score }}</strong><small>/ 100</small></div>

    <div class="security-metrics">
      <div><span>{{ alert.window_sec }} 秒内改写</span><b>{{ alert.files_modified }}</b></div>
      <div><span>批量重命名</span><b>{{ alert.files_renamed }}</b></div>
      <div><span>扩展名变化</span><b>{{ alert.extensions_changed }}</b></div>
      <div><span>高熵写入</span><b>{{ alert.entropy_anomalies }}</b></div>
    </div>

    <div class="threat-source">
      <span>疑似来源</span>
      <strong>{{ alert.source.kind === 'docker' ? `Docker · ${alert.source.container_name}` : alert.source.command || '未知进程' }}</strong>
      <small v-if="alert.source.pid">PID {{ alert.source.pid }} · 写入 {{ alert.write_mib_sec.toFixed(1) }} MiB/s</small>
    </div>

    <div class="affected-path">
      <span>受影响文件（安全取证）</span>
      <code v-for="path in alert.sample_paths.slice(0, 3)" :key="path">{{ path }}</code>
      <code v-if="!alert.sample_paths.length">正在收集具体路径...</code>
    </div>

    <div class="warning-action">
      <b>{{ alert.auto_contained ? '已自动隔离来源' : '仅报警，尚未自动阻断' }}</b>
      <button type="button" @click="$emit('acknowledge')">我已看到</button>
    </div>
  </section>
</template>
