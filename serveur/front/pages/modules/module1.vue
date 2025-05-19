<template>
  <div class="module1-container">
    <img
      v-if="backgroundPath"
      :src="`${apiUrl}/getAsset?module=1&path=${backgroundPath}`"
      class="fullscreen-img"
      :style="{ filter: filterStyle }"
    />
    <div
      v-if="showDebug"
      class="debug-circle"
      :style="circleStyle"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { useRuntimeConfig } from '#app'
import { computed } from 'vue'
import useModule1 from '~/composables/module1.ts'

definePageMeta({ layout: 'module' })

const { public: { apiUrl } } = useRuntimeConfig()
const { backgroundPath, filterStyle, x, y, diamPx } = useModule1()

// Pour afficher le cercle de debug si nécessaire
const showDebug = computed(() =>
  new URLSearchParams(window.location.search).get('debug') === '1'
)
const circleStyle = computed(() => ({
  position: 'absolute',
  left: `${(x.value / 320) * 100}%`,
  top: `${(y.value / 240) * 100}%`,
  width: `${diamPx.value}px`,
  height: `${diamPx.value}px`,
  border: '2px solid red',
  borderRadius: '50%',
  transform: 'translate(-50%, -50%)',
  pointerEvents: 'none',
  boxSizing: 'border-box',
  zIndex: 10,
}))
</script>

<style scoped src="~/assets/modules/1/style.css"></style>
