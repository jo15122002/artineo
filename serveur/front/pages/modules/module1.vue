<template>
  <div class="module1-container">
    <img
      v-if="backgroundPath"
      :src="`${apiBase}/getAsset?module=1&path=${backgroundPath}`"
      class="fullscreen-img"
      :style="{ filter: filterStyle }"
    />
    <!-- debug circle -->
    <div
      v-if="showDebug"
      class="debug-circle"
      :style="circleStyle"
    ></div>
  </div>
</template>

<script setup>
import { useRuntimeConfig } from '#app'
import { computed } from 'vue'
import use1ir from '~/composables/module1'

definePageMeta({ layout: 'module' })

const { public: { apiBase } } = useRuntimeConfig()
const { filterStyle, showDebug, x, y, diamPx } = use1ir()

// Calcul du style de position/taille du cercle de debug
const circleStyle = computed(() => ({
  position:      'absolute',
  left:          `${(x.value / 320) * 100}%`,
  top:           `${(y.value / 240) * 100}%`,
  width:         `${diamPx.value}px`,
  height:        `${diamPx.value}px`,
  border:        '2px solid red',
  'border-radius': '50%',
  transform:     'translate(-50%, -50%)',
  'pointer-events': 'none',
  'box-sizing':  'border-box'
}))
</script>

<style scoped src="~/assets/modules/1/style.css"></style>

<style scoped>
/* Si besoin, override sur la zone debug */
.debug-circle {
  z-index: 10;
}
</style>
