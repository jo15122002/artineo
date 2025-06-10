<template>
  <div class="module2-container">
    <canvas ref="canvas" />
  </div>
</template>

<script setup lang="ts">
// On importe uniquement la ref et le composable
import { ref } from 'vue'
import useModule2 from '~/composables/module2'

definePageMeta({ layout: 'module' })

// 1) On crée la ref vers le <canvas>
const canvas = ref<HTMLCanvasElement | null>(null)

// 2) On appelle le composable :
//    il va initialiser Three.js, charger OBJ/MTL, démarrer WS/polling, etc.
useModule2(canvas)
</script>

<style scoped src="~/assets/modules/2/style.css"></style>
