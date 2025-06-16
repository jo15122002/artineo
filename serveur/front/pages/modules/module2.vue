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
         <div>
          <div class="button rectX-button" ref="rectXBtn">
          <img src="~/assets/modules/2/rectX.svg" alt="Slider X" />
          <div class="rect-selector" ref="rectXSel" :style="{ '--t-x': translateX + 'px' }" />
        </div>
        <span v-if="isXChecked">V</span>
         </div>
        

        <!-- Slider Y --><div>
        <div class="button rectY-button" ref="rectYBtn" :class="{'gray': !isXChecked}">
          <img src="~/assets/modules/2/rectY.svg" alt="Slider Y" />
          <div class="rect-selector" ref="rectYSel" :style="{ '--t-y': translateY + 'px' }" />
        </div>
        <span v-if="isYChecked">V</span>
         </div>

        <!-- Knob Z --><div>
        <div class="button circle-button" :class="{'gray': !isXChecked || !isYChecked}">
          <img src="~/assets/modules/2/circle.svg" alt="Knob Z" />
          <div class="rect-selector" :style="{ transform: `rotate(${rotZDeg}deg) translateY(-115px)` }" />
        </div>
        <span v-if="isZChecked">V</span>
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

// Canvas + hook composable
const canvas = ref<HTMLCanvasElement | null>(null)
const {
  rotX, rotY, rotZ,
  rotXMin, rotXMax,
  rotYMin, rotYMax,
  rotZMin, rotZMax,
  timerColor, timerText,
  isXChecked, isYChecked, isZChecked
} = useModule2(canvas)

// normalisation dynamique X/Y/Z selon les bornes chargées
const pctX = computed(() =>
  (rotX.value - rotXMin.value) / (rotXMax.value - rotXMin.value)
)
const pctY = computed(() =>
  (rotY.value - rotYMin.value) / (rotYMax.value - rotYMin.value)
)
const pctZ = computed(() =>
  (rotZ.value - rotZMin.value) / (rotZMax.value - rotZMin.value)
)

// Refs to DOM for sliders
const rectXBtn = ref<HTMLElement | null>(null)
const rectXSel = ref<HTMLElement | null>(null)
const rectYBtn = ref<HTMLElement | null>(null)
const rectYSel = ref<HTMLElement | null>(null)

// Measured dims
const parentWidthX = ref(0)
const selectorWidth = ref(0)
const parentHeightY = ref(0)
const selectorHeight = ref(0)

// Compute translations (pixels)
const translateX = computed(() =>
  pctX.value * (parentWidthX.value - selectorWidth.value)
)
const translateY = computed(() =>
  pctY.value * (parentHeightY.value - selectorHeight.value)
)

// Compute knob rotation in degrees (0–360°)
const rotZDeg = computed(() => pctZ.value * 360)

let roX: ReturnType<typeof useResizeObserver>
let roY: ReturnType<typeof useResizeObserver>

onMounted(() => {
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
