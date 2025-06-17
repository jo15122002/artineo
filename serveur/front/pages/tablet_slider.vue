<template>
    <div class="module2-page">
        <h1>Module 2 – Simulation</h1>

        <div v-show="!isXChecked" class="controls module2-controls">
          <div>
            <div class="button rectX-button" ref="rectXBtn">
              <img src="~/assets/modules/2/rectX.svg" alt="Slider X" />
              <div class="rect-selector" ref="rectXSel" :style="{ '--t-x': translateX + 'px' }" />
            </div>
            <img v-if="isXChecked" src="~/assets/modules/2/splash-check.png" alt="splash check" class="splash-check" />
          </div>
         <div>
          <div v-show="isXChecked && !isYChecked" class="button rectY-button" ref="rectYBtn">
            <img src="~/assets/modules/2/rectY.svg" alt="Slider Y" />
            <div class="rect-selector" ref="rectYSel" :style="{ '--t-y': translateY + 'px' }" />
          </div>
          <img v-if="isYChecked" src="~/assets/modules/2/splash-check.png" alt="splash check" class="splash-check" />
        </div>
          <div v-show="isYChecked && !isZChecked">
            <div class="button circle-button" :class="{'gray': !isXChecked || !isYChecked}">
              <img src="~/assets/modules/2/circle.svg" alt="Knob Z" />
              <div class="rect-selector" :style="{ transform: `rotate(${rotZDeg}deg) translateY(-115px)` }" />
            </div>
            <img v-if="isYChecked" src="~/assets/modules/2/splash-check.png" alt="splash check" class="splash-check" />
          </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import {computed, onBeforeUnmount, onMounted, onUnmounted, reactive, ref} from 'vue'
import { useArtineo } from '~/composables/useArtineo'
import {useResizeObserver} from "@vueuse/core";
import {clamp} from "@antfu/utils";
const rotX = ref(0)
const rotY = ref(0)
const rotZ = ref(0)
const rotXMin = ref(-Infinity)
const rotXMax = ref(+Infinity)
const rotYMin = ref(-Infinity)
const rotYMax = ref(+Infinity)
const rotZMin = ref(-Infinity)
const rotZMax = ref(+Infinity)

const pctX = computed(() => {
  const denom = rotXMax.value - rotXMin.value
  return denom !== 0 ? (rotX.value - rotXMin.value) / denom : 0
})
const pctY = computed(() => {
  const denom = rotYMax.value - rotYMin.value
  return denom !== 0 ? (rotY.value - rotYMin.value) / denom : 0
})
const pctZ = computed(() => {
  const denom = rotZMax.value - rotZMin.value
  return denom !== 0 ? (rotZ.value - rotZMin.value) / denom : 0
})

const rectXBtn = ref<HTMLElement>()
const rectXSel = ref<HTMLElement>()
const rectYBtn = ref<HTMLElement>()
const rectYSel = ref<HTMLElement>()

// Measured dims
const parentWidthX = ref(0)
const selectorWidth = ref(0)
const parentHeightY = ref(0)
const selectorHeight = ref(0)

// Compute translations (pixels)
const translateX = computed(() =>
    isFinite(pctX.value) && isFinite(parentWidthX.value) && isFinite(selectorWidth.value)
        ? pctX.value * (parentWidthX.value - selectorWidth.value)
        : 0
)
const translateY = computed(() =>
    isFinite(pctY.value) && isFinite(parentHeightY.value) && isFinite(selectorHeight.value)
        ? pctY.value * (parentHeightY.value - selectorHeight.value)
        : 0
)

// Compute knob rotation in degrees (0–360°)
const rotZDeg = computed(() => pctZ.value * 360)

const tolerance = 0.2 // tolérance pour les rotations
const objectiveRotX = 2
const objectiveRotY = 1
const objectiveRotZ = 0.5
const isXChecked = computed(() => Math.abs(rotX.value - objectiveRotX) < tolerance)
const isYChecked = computed(() => Math.abs(rotY.value - objectiveRotY) < tolerance)
const isZChecked = computed(() => Math.abs(rotZ.value - objectiveRotZ) < tolerance)

const client = useArtineo(2)
let intervalId: number | null = null

function sendModule2() {

    client.setBuffer({
        rotX: rotX.value,
        rotY: rotY.value,
        rotZ: rotZ.value,
        isXChecked: isXChecked.value,
        isYChecked: isYChecked.value,
        isZChecked: isZChecked.value
    })
}

let roX: ReturnType<typeof useResizeObserver>
let roY: ReturnType<typeof useResizeObserver>

async function loadConfig() {
  try {
    console.log("loadConfig", client)
    const cfg = await client.fetchConfig()
    console.log('Config rotation:', cfg)
    // ex. { axes: { rotX: { min:…, max:… }, … } }
    rotXMin.value = cfg.axes.rotX.min  ?? rotXMin.value
    rotXMax.value = cfg.axes.rotX.max  ?? rotXMax.value
    rotYMin.value = cfg.axes.rotY.min  ?? rotYMin.value
    rotYMax.value = cfg.axes.rotY.max  ?? rotYMax.value
    rotZMin.value = cfg.axes.rotZ.min  ?? rotZMin.value
    rotZMax.value = cfg.axes.rotZ.max  ?? rotZMax.value
  } catch (e) {
    console.warn('Impossible de charger la config rotation', e)
  }
}

onMounted(() => {
    // Envoi continu automatique toutes les 100 ms
    intervalId = window.setInterval(sendModule2, 100)
    void loadConfig()
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
  setupDragX()
  setupDragY()
  setupDragZ()
})

onBeforeUnmount(() => {
  roX?.stop()
  roY?.stop()
})

onUnmounted(() => {
    if (intervalId !== null) {
        clearInterval(intervalId)
    }
})

function setupDragX() {
  const el = rectXSel.value
  const parent = rectXBtn.value
  if (!el || !parent) return

  const onMouseMove = (e: MouseEvent) => {
    console.log('Mouse move on X slider', e.clientX)
    const rect = parent.getBoundingClientRect()
    const offsetX = e.clientX - rect.left
    const pct = clamp(offsetX / rect.width, 0, 1)
    console.log('Offset X:', offsetX, 'Pct:', pct)
    console.log('RotXMin:', rotXMin.value, 'RotXMax:', rotXMax.value)
    rotX.value = rotXMin.value + pct * (rotXMax.value - rotXMin.value)
  }

  const onMouseUp = () => {
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
  }

  el.addEventListener('mousedown', () => {
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
  })
}

function setupDragY() {
  const el = rectYSel.value
  const parent = rectYBtn.value
  if (!el || !parent) return

  const onMouseMove = (e: MouseEvent) => {
    const rect = parent.getBoundingClientRect()
    const offsetY = e.clientY - rect.top
    const pct = clamp(offsetY / rect.height, 0, 1)
    rotY.value = rotYMin.value + pct * (rotYMax.value - rotYMin.value)
  }

  const onMouseUp = () => {
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
  }

  el.addEventListener('mousedown', () => {
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
  })
}

function setupDragZ() {
  const el = document.querySelector('.circle-button > .rect-selector') as HTMLElement | null
  const parent = document.querySelector('.circle-button') as HTMLElement | null
  if (!el || !parent) return

  const onMouseMove = (e: MouseEvent) => {
    const rect = parent.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    const dx = e.clientX - centerX
    const dy = e.clientY - centerY
    const angleRad = Math.atan2(dy, dx)
    const angleDeg = ((angleRad * 180) / Math.PI + 360) % 360
    const pct = angleDeg / 360
    rotZ.value = rotZMin.value + pct * (rotZMax.value - rotZMin.value)
  }

  const onMouseUp = () => {
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
  }

  el.addEventListener('mousedown', () => {
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
  })
}
</script>

<style scoped>
@font-face {
    font-family: "CheeseSauce";
    src: url('./Cheese-Sauce.woff2') format("woff2");
}

.module2-page {
    padding: 2rem;
    font-family: "CheeseSauce", sans-serif;
    max-width: 400px;
    margin: auto;
}

.module2-controls label {
    display: flex;
    align-items: center;
    margin: 0.5rem 0;
}

.module2-controls input[type='range'] {
    margin: 0 0.5rem;
    flex: 1;
}

.module2-controls span {
    width: 60px;
    text-align: right;
    font-family: monospace;
}

.button-row {
    margin-top: 1rem;
}

.button-row button {
    padding: 0.5rem 1rem;
    font-size: 1rem;
    cursor: pointer;
}
</style>

<style scoped src="~/assets/modules/2/style.css"></style>
