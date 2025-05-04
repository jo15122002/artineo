<template>
    <div class="module4-container">
      <canvas ref="canvas" />
    </div>
  </template>
  
  <script setup>
  import { onMounted, ref } from 'vue'
import use4kinect from '~/composables/module4'
  
  definePageMeta({ layout: 'module' })
  
  const canvas = ref(null)
  
  onMounted(() => {
    // taille ROI 170×250, zoom ×3
    const ROISz = { w: 250, h: 170, scale: 3 }
    const c = canvas.value
    c.width  = ROISz.w * ROISz.scale
    c.height = ROISz.h * ROISz.scale
    use4kinect(canvas)
  })
  </script>
  
  <style scoped src="~/assets/modules/4/style.css"></style>
  <style scoped>
  
  </style>  