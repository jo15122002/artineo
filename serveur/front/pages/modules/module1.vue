<template>
  <div class="module1-container">
    <img v-if="backgroundPath" :src="`${apiUrl}/getAsset?module=1&path=${backgroundPath}`" class="fullscreen-img"
      :style="{ filter: filterStyle }" />

    <!-- Zone cible (si debug=true) -->
    <div v-if="showDebug" class="debug-zone" :style="zoneStyle"></div>

    <!-- Cercle de détection IR (si debug=true) -->
    <div v-if="showDebug" class="debug-circle" :style="circleStyle"></div>
  </div>
</template>

<script setup lang="ts">
import { useRuntimeConfig } from '#app'
import { computed, onMounted, ref } from 'vue'
import useModule1 from '~/composables/module1.ts'

definePageMeta({ layout: 'module' })

const { public: { apiUrl } } = useRuntimeConfig()
const { backgroundPath, filterStyle, x, y, diamPx } = useModule1()

// ────────────────────────────────────────────────────────────────────────────
// 1) PARAMÈTRE debug dans l’URL (côté CLIENT uniquement)
// ────────────────────────────────────────────────────────────────────────────
const showDebug = ref(false)

onMounted(() => {
  const params = new URLSearchParams(window.location.search)
  showDebug.value = params.get('debug') === 'true'
})

// ────────────────────────────────────────────────────────────────────────────
// 2) Définition de la “zone cible” fixe (x=160, y=120, rayon=30px)
// ────────────────────────────────────────────────────────────────────────────
const goodResponsePosition = { x: 160, y: 120 }
const goodResponseZoneSize = 30

// Calcul du style ajusté au conteneur (320×240 → 100%×100%)
const zoneStyle = computed(() => ({
  position: 'absolute',
  left: `${(goodResponsePosition.x / 320) * 100}%`,
  top: `${(goodResponsePosition.y / 240) * 100}%`,
  width: `${goodResponseZoneSize * 2}px`,
  height: `${goodResponseZoneSize * 2}px`,
  border: '2px dashed red',
  borderRadius: '50%',
  transform: 'translate(-50%, -50%)',
  pointerEvents: 'none',
  boxSizing: 'border-box',
  zIndex: 10,
}))

// ────────────────────────────────────────────────────────────────────────────
// 3) Style du cercle de détection IR (x, y, diamPx)
// ────────────────────────────────────────────────────────────────────────────
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
  zIndex: 11,
}))
</script>

<style scoped src="~/assets/modules/1/style.css"></style>
