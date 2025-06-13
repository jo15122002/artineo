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
      <img src="~/assets/modules/4/images/arty.png" alt="">
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import use4kinect from '~/composables/module4.ts'

definePageMeta({ layout: 'module' })

// 1️⃣ Réf du canvas
const canvas = ref<HTMLCanvasElement | null>(null)

// 2️⃣ Appel du composable AU TOP-LEVEL
const { strokes, objects, timerColor, timerText } = use4kinect(canvas)

// 3️⃣ Initialisation de la taille après montage
onMounted(() => {
  // ROI SIZE
  const ROISz = { w: 305, h: 200, scale: 3 }
  const c = canvas.value!
  c.width  = ROISz.w * ROISz.scale
  c.height = ROISz.h * ROISz.scale
})
</script>

<style scoped src="~/assets/modules/4/style.css"></style>
