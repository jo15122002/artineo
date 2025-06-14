<template>
  <div class="module1-container">
    <div class="painting-frame-with-shadow">
      <div class="painting-frame">
        <div class="painting-container">
          <img v-if="backgroundPath" :src="`${apiUrl}/getAsset?module=1&path=${backgroundPath}`" class="fullscreen-img"
            :style="{ filter: filterStyle }" />
        </div>
      </div>
    </div>

    <div class="timer" :style="{ '--timer-color': timerColor }">
      <div class="timer-splat"></div>
      <span class="timer-text">{{ timerText }}</span>
    </div>

    <div class="arty">
      <!-- image fixe -->
      <img src="~/assets/modules/4/images/arty.png" alt="Arty" class="arty-img" />

      <!-- image dynamique -->
      <img :src="stepSrc" alt="Indication step" class="indication-step" />
    </div>
    <!-- Zone cible (si debug=true) -->
    <div v-if="showDebug" class="debug-zone" :style="zoneStyle"></div>

    <!-- Cercle de détection IR (si debug=true) -->
    <div v-if="showDebug" class="debug-circle" :style="circleStyle"></div>
  </div>
</template>

<script setup lang="ts">
import { useRuntimeConfig } from '#app';
import { computed, onMounted, reactive, ref } from 'vue'; // ajout de reactive
import useModule1 from '~/composables/module1.ts';

definePageMeta({ layout: 'module' })

const { public: { apiUrl } } = useRuntimeConfig()
const { backgroundPath, filterStyle, x, y, diamPx, timerColor, timerText } = useModule1()

// 🟢 Étape courante
const step = ref(1)

const images = import.meta.glob(
  '~/assets/modules/1/steps/*.png',
  { eager: true, as: 'url' }
) as Record<string, string>

// 🔄 Computed pour retourner l'URL correspondant à la step courante
const stepSrc = computed(() => {
  const entry = Object.entries(images)
    .find(([path]) => path.endsWith(`step${step.value}.png`))
  return entry ? entry[1] : ''
})

// debug flag
const showDebug = ref(false)

// reactive pour la position, initialisée à 0
const goodResponsePosition = reactive({ x: 0, y: 0 })
const goodResponseZoneSize = 30

onMounted(() => {
  const params = new URLSearchParams(window.location.search)
  showDebug.value = params.get('debug') === 'true' || params.get('debug') === '1'

  // génération aléatoire dans [0,320]×[0,240]
  goodResponsePosition.x = Math.random() * 320
  goodResponsePosition.y = Math.random() * 240
})

// style de la zone cible
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
