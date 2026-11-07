<script setup lang="ts">
import { ref } from 'vue'
import girlSprite from '../assets/mascot/girl-sprite.webp'

const props = defineProps<{ initialName: string; mode?: 'first-run' | 'edit'; saving?: boolean; serverError?: string }>()
const emit = defineEmits<{ save: [name: string]; cancel: [] }>()
const name = ref(props.initialName)
const error = ref('')

function submit() {
  const value = name.value.trim()
  if (!value) { error.value = '请给她取一个名字'; return }
  if (value.length > 12) { error.value = '名字最多 12 个字'; return }
  error.value = ''
  emit('save', value)
}
</script>

<template>
  <section class="name-setup" aria-labelledby="name-setup-title">
    <div class="name-setup-portrait"><img :src="girlSprite" alt="Q版小女孩在使用电脑" /></div>
    <div class="name-setup-copy">
      <h1 id="name-setup-title">{{ mode === 'edit' ? '修改她的名字' : '欢迎使用 R1 屏幕' }}</h1>
      <p>{{ mode === 'edit' ? '新名字会同步到开场页和快捷入口。' : '先给正在守护 NAS 的小女孩取个名字。以后可以随时修改。' }}</p>
    </div>
    <form @submit.prevent="submit">
      <label for="mascot-name">她叫什么？</label>
      <input id="mascot-name" v-model="name" maxlength="12" autocomplete="off" placeholder="例如：娴宝" autofocus />
      <small v-if="error || serverError" role="alert">{{ error || serverError }}</small>
      <button type="submit" :disabled="saving">{{ saving ? '正在保存…' : '保存并进入' }}</button>
      <button v-if="mode === 'edit'" class="name-cancel" type="button" :disabled="saving" @click="emit('cancel')">取消</button>
    </form>
  </section>
</template>
