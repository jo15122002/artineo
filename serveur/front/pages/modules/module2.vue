<template>
  <div class="module2-container">
    <div class="frame-and-buttons-wrapper">
      <div class="frame-shadow">
        <div class="frame">
          <canvas ref="canvas" />
        </div>
      </div>
      <div class="buttons-wrapper" ref="buttonsWrapper">

        <!-- Slider X -->
        <div class="button rectX-button" ref="rectXBtn">
          <img src="~/assets/modules/2/rectX.svg" alt="Slider X" />
          <div class="rect-selector" ref="rectXSel" :style="{ '--t-x': translateY + 'px' }" />
        </div>

        <!-- Slider Y -->
        <div class="button rectY-button" ref="rectYBtn">
          <img src="~/assets/modules/2/rectY.svg" alt="Slider Y" />
          <div class="rect-selector" ref="rectYSel" :style="{ '--t-y': translateX + 'px' }" />
        </div>

        <!-- Knob Z -->
        <div class="button circle-button">
          <img src="~/assets/modules/2/circle.svg" alt="Knob Z" />
          <div class="rect-selector" :style="{ transform: `rotate(${rotZDeg}deg) translateY(-115px)` }" />
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
import { useResizeObserver } from '@vueuse/core'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import useModule2 from '~/composables/module2'

// 🟢 Étape courante
const step = ref(1)

const images = import.meta.glob(
  '~/assets/modules/3/steps/*.png',
  { eager: true, as: 'url' }
) as Record<string, string>

// 🔄 Computed pour retourner l'URL correspondant à la step courante
const stepSrc = computed(() => {
  const entry = Object.entries(images)
    .find(([path]) => path.endsWith(`step${step.value}.png`))
  return entry ? entry[1] : ''
})

// Canvas + rotations
const canvas = ref<HTMLCanvasElement | null>(null)
const { rotX, rotY, rotZ, timerColor, timerText } = useModule2(canvas)

// Convert rotZ to degrees for CSS
const rotZDeg = computed(() => (rotZ.value * 180) / Math.PI)

// Percentage normalization (±2π → 0–1)
const inf = -2 * Math.PI
const sup = 2 * Math.PI
const span = sup - inf
const norm = (v: number) => (v - inf) / span
const pctX = computed(() => norm(rotX.value))
const pctY = computed(() => norm(rotY.value))

// Refs to DOM
const rectXBtn = ref<HTMLElement | null>(null)
const rectXSel = ref<HTMLElement | null>(null)
const rectYBtn = ref<HTMLElement | null>(null)
const rectYSel = ref<HTMLElement | null>(null)

// Measured dims
const parentWidthX = ref(0)
const selectorWidth = ref(0)
const parentHeightY = ref(0)
const selectorHeight = ref(0)

// Compute translations (%)
const translateX = computed(() =>
  pctX.value * (parentWidthX.value - selectorWidth.value)
)
const translateY = computed(() =>
  pctY.value * (parentHeightY.value - selectorHeight.value)
)

let roX: ReturnType<typeof useResizeObserver>
let roY: ReturnType<typeof useResizeObserver>

onMounted(() => {
  // mesure initiale + création des observers
  const measure = () => {
    if (rectXBtn.value) parentWidthX.value = rectXBtn.value.clientWidth
    if (rectXSel.value) selectorWidth.value = rectXSel.value.offsetWidth
    if (rectYBtn.value) parentHeightY.value = rectYBtn.value.clientHeight
    if (rectYSel.value) selectorHeight.value = rectYSel.value.offsetHeight
  }

  measure()

  if (rectXBtn.value) {
    roX = useResizeObserver(rectXBtn, measure)
  }
  if (rectYBtn.value) {
    roY = useResizeObserver(rectYBtn, measure)
  }
})

onBeforeUnmount(() => {
  roX?.stop()
  roY?.stop()
})
</script>

<style scoped src="~/assets/modules/2/style.css"></style>
