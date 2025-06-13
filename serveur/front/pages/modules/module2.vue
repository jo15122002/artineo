<template>
  <div class="module2-container">
    <div class="frame-and-buttons-wrapper">
      <div class="frame-shadow">
        <div class="frame">
          <canvas ref="canvas" />
        </div>
      </div>
      <div class="buttons-wrapper">

        <!-- Bouton X -->
        <div class="button rectX-button" ref="rectXBtn">
          <img src="~/assets/modules/2/rectX.svg" alt="Rect X Button" />
          <div class="rect-selector" ref="rectXSel" :style="{ transform: `translateX(${translateX}px)` }" />
        </div>

        <!-- Bouton Y -->
        <div class="button rectY-button" ref="rectYBtn">
          <img src="~/assets/modules/2/rectY.svg" alt="Rect Y Button" />
          <div class="rect-selector" ref="rectYSel"
            :style="{ transform: `translateY(${translateY}px) rotate(90deg)` }" />
        </div>

        <!-- Cercle inchangé… -->
        <div class="button circle-button">
          <img src="~/assets/modules/2/circle.svg" alt="Circle Button" />
          <div class="rect-selector"
            :style="{ transform: `translateY(-115px)`, rotate: `calc(${percentageRotate} * 180deg)` }" />
        </div>

      </div>
    </div>

    <div class="timer" :style="{ '--timer-color': timerColor }">
      <div class="timer-splat"></div>
      <span class="timer-text">{{ timerText }}</span>
    </div>

    <div class="arty">
      <img src="~/assets/modules/2/arty.png" alt="">
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import useModule2 from '~/composables/module2'

// 1) récupère rotX/Y/Z
const canvas = ref<HTMLCanvasElement | null>(null)
const { rotX, rotY, rotZ, timerColor, timerText } = useModule2(canvas)

// 2) bornes ±2π
const inf = -2 * Math.PI
const sup = 2 * Math.PI
const span = sup - inf
const norm = (v: number) => (v - inf) / span

const percentageX = computed(() => norm(rotX.value))
const percentageY = computed(() => norm(rotY.value))
const percentageRotate = computed(() => norm(rotZ.value))

// 3) refs vers les parents et sélecteurs
const rectXBtn = ref<HTMLElement | null>(null)
const rectXSel = ref<HTMLElement | null>(null)
const rectYBtn = ref<HTMLElement | null>(null)
const rectYSel = ref<HTMLElement | null>(null)

// 4) dims mesurées
const parentWidthX = ref(0)
const selectorWidth = ref(0)
const parentHeightY = ref(0)
const selectorHeight = ref(0)

onMounted(() => {
  // X
  if (rectXBtn.value) parentWidthX.value = rectXBtn.value.clientWidth
  if (rectXSel.value) selectorWidth.value = rectXSel.value.offsetWidth
  // Y
  if (rectYBtn.value) parentHeightY.value = rectYBtn.value.clientHeight
  if (rectYSel.value) selectorHeight.value = rectYSel.value.offsetHeight
})

// 5) calculs px
const translateX = computed(() =>
  percentageX.value * (parentWidthX.value - selectorWidth.value)
)
const translateY = computed(() =>
  percentageY.value * (parentHeightY.value - selectorHeight.value)
)
</script>

<style scoped src="~/assets/modules/2/style.css"></style>
