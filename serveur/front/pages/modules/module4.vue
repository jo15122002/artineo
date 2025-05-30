<template>
  <div class="module4-container">
    <canvas ref="canvas" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import use4kinect from '~/composables/module4.ts'

definePageMeta({ layout: 'module' })

// 1️⃣ Réf du canvas
const canvas = ref<HTMLCanvasElement | null>(null)

// 2️⃣ Appel du composable AU TOP-LEVEL
const { strokes, objects } = use4kinect(canvas)

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
