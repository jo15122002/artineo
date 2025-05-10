<template>
  <div class="module1-container">
    <!-- Fond uniquement si backgroundPath existe -->
    <img
      v-if="backgroundPath"
      :src="`${apiUrl}/getAsset?module=1&path=${backgroundPath}`"
      class="fullscreen-img"
      :style="{ filter: filterStyle }"
    />

    <!-- Cercle de debug si ?debug=1 -->
    <div
      v-if="showDebug"
      class="debug-circle"
      :style="circleStyle"
    ></div>
  </div>
</template>

<script setup>
import { useRuntimeConfig } from '#app';
import { computed } from 'vue';
import use1ir from '~/composables/module1.js';

definePageMeta({ layout: 'module' })

// On récupère bien apiUrl (et non apiBase)
const { public: { apiUrl } } = useRuntimeConfig()

// On appelle la composable
const {
  filterStyle,
  showDebug,
  x, y, diamPx,
  backgroundPath
} = use1ir()

// Style du cercle de debug (inchangé)
const circleStyle = computed(() => ({
  position:        'absolute',
  left:            `${(x.value / 320) * 100}%`,
  top:             `${(y.value / 240) * 100}%`,
  width:           `${diamPx.value}px`,
  height:          `${diamPx.value}px`,
  border:          '2px solid red',
  'border-radius': '50%',
  transform:       'translate(-50%, -50%)',
  'pointer-events':'none',
  'box-sizing':    'border-box',
  'z-index':       10
}))
</script>

<style scoped src="~/assets/modules/1/style.css"></style>
