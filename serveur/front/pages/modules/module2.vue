<template>
  <div class="module2-container">
    <div class="frame-and-buttons-wrapper">
      <div class="frame-shadow">
        <div class="frame">
          <canvas ref="canvas" />
        </div>
      </div>
      <div class="buttons-wrapper">
        <div class="button rectX-button">
          <img src="~/assets/modules/2/rectX.svg" alt="Rect X Button" />
          <div class="rect-selector"
               :style="{ transform: `translateX(calc(${percentageX} * 193px))` }"
          />
        </div>
        <div class="button rectY-button">
          <img src="~/assets/modules/2/rectY.svg" alt="Rect Y Button" />
          <div class="rect-selector"
                :style="{ transform: `translateX(calc(${percentageY} * -143px))` }"
          />
        </div>
        <div class="button circle-button">
          <img src="~/assets/modules/2/circle.svg" alt="Circle Button" />
          <div class="rect-selector"
          :style="{ transform: `translateY(-115px)`, rotate: `calc(${percentageRotate} * 180deg)` }"/>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// On importe uniquement la ref et le composable
import { ref } from 'vue'
import useModule2 from '~/composables/module2'

definePageMeta({ layout: 'module' })

// 1) On crée la ref vers le <canvas>
const canvas = ref<HTMLCanvasElement | null>(null)

const percentageX = ref(0.2) // Valeur entre -1 et 1 pour la position X du rectangle
const percentageY = ref(0.2) // Valeur entre -1 et 1 pour la position Y du rectangle
const percentageRotate = ref(0.2) // Valeur entre -1 et 1 pour la rotation du cercle

// 2) On appelle le composable :
//    il va initialiser Three.js, charger OBJ/MTL, démarrer WS/polling, etc.
useModule2(canvas)
</script>

<style scoped src="~/assets/modules/2/style.css"></style>
