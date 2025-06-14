<template>
  <div class="module4-container">
    <div class="painting-frame-with-shadow">
      <div class="painting-frame">
        <div class="painting-container">
          <canvas ref="canvas" />
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
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import use4kinect from '~/composables/module4.ts'

definePageMeta({ layout: 'module' })

// 🟢 Étape courante
const step = ref(1)

// 📦 Import de toutes les étapes en “eager” (chargées au build) et renvoi d'URL
const images = import.meta.glob(
  '~/assets/modules/4/images/steps/*.png',
  { eager: true, as: 'url' }
) as Record<string, string>

// 🔄 Computed pour retourner l'URL correspondant à la step courante
const stepSrc = computed(() => {
  const entry = Object.entries(images)
    .find(([path]) => path.endsWith(`step${step.value}.png`))
  return entry ? entry[1] : ''
})

// Réf du canvas pour le composable
const canvas = ref<HTMLCanvasElement | null>(null)

// Appel au composable Kinect
const { strokes, objects, timerColor, timerText, timerSeconds, startTimer } = use4kinect(canvas, step)

// Calcul dynamique du nombre total d’étapes  
const maxStep = Object.keys(images)
  .map(path => {
    const m = path.match(/step(\d+)\.png$/)
    return m ? parseInt(m[1], 10) : 0
  })
  .reduce((a, b) => Math.max(a, b), 0)

// Watcher : quand timer arrive à 0 et qu’il reste une étape, on incrémente et on relance
watch(timerSeconds!, newVal => {
  if (newVal === 0 && step.value < maxStep) {
    step.value++
    startTimer?.()
  }
})

// Initialisation de la taille du canvas au montage
onMounted(() => {
  const ROISz = { w: 305, h: 200, scale: 3 }
  const c = canvas.value!
  c.width = ROISz.w * ROISz.scale
  c.height = ROISz.h * ROISz.scale
})
</script>

<style scoped src="~/assets/modules/4/style.css"></style>
