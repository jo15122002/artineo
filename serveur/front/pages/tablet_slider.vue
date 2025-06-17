<template>
  <div class="module2-page">
    <h1>Module 2 – Simulation</h1>

    <div class="controls module2-controls">
      <div v-show="!isXChecked">
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
        <div class="button circle-button" :class="{ gray: !isXChecked || !isYChecked }">
          <img src="~/assets/modules/2/circle.svg" alt="Knob Z" />
          <div class="rect-selector" :style="{ transform: `rotate(${rotZDeg}deg) translateY(-115px)` }" />
        </div>
        <img v-if="isYChecked" src="~/assets/modules/2/splash-check.png" alt="splash check" class="splash-check" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, onUnmounted } from 'vue'
import { useArtineo } from '~/composables/useArtineo'
import { useResizeObserver } from '@vueuse/core'
import { clamp } from '@antfu/utils'

// --- rotations and bounds ---
const rotX = ref(0)
const rotY = ref(0)
const rotZ = ref(0)

const rotXMin = ref(-Infinity)
const rotXMax = ref(+Infinity)
const rotYMin = ref(-Infinity)
const rotYMax = ref(+Infinity)
const rotZMin = ref(-Infinity)
const rotZMax = ref(+Infinity)

// --- compute percentage along each axis ---
const pctX = computed(() =>
  rotXMin.value < rotXMax.value
    ? (rotX.value - rotXMin.value) / (rotXMax.value - rotXMin.value)
    : 0
)
const pctY = computed(() =>
  rotYMin.value < rotYMax.value
    ? (rotY.value - rotYMin.value) / (rotYMax.value - rotYMin.value)
    : 0
)
const pctZ = computed(() =>
  rotZMin.value < rotZMax.value
    ? (rotZ.value - rotZMin.value) / (rotZMax.value - rotZMin.value)
    : 0
)

// --- slider positions in px and rotation in deg ---
const parentWidthX = ref(0)
const selectorWidth = ref(0)
const parentHeightY = ref(0)
const selectorHeight = ref(0)

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
const rotZDeg = computed(() => pctZ.value * 360)

// --- check states ---
const tolerance = 0.2
const objectiveRotX = 2
const objectiveRotY = 1
const objectiveRotZ = 0.5
const isXChecked = computed(() => Math.abs(rotX.value - objectiveRotX) < tolerance)
const isYChecked = computed(() => Math.abs(rotY.value - objectiveRotY) < tolerance)
const isZChecked = computed(() => Math.abs(rotZ.value - objectiveRotZ) < tolerance)

// --- DOM refs ---
const rectXBtn = ref<HTMLElement>()
const rectXSel = ref<HTMLElement>()
const rectYBtn = ref<HTMLElement>()
const rectYSel = ref<HTMLElement>()

// --- server buffering ---
const client = useArtineo(2)
let intervalId: number | null = null
function sendModule2() {
  console.log("send", {
    rotX: rotX.value,
    rotY: rotY.value,
    rotZ: rotZ.value,
    isXChecked: isXChecked.value,
    isYChecked: isYChecked.value,
    isZChecked: isZChecked.value,
  });

  client.setBuffer({
    rotX: rotX.value,
    rotY: rotY.value,
    rotZ: rotZ.value,
    isXChecked: isXChecked.value,
    isYChecked: isYChecked.value,
    isZChecked: isZChecked.value,
  })
}

// --- load config, set bounds, init slider at min ---
async function loadConfig() {
  try {
    const cfg = await client.fetchConfig()
    rotXMin.value = cfg.axes.rotX.min
    rotXMax.value = cfg.axes.rotX.max
    rotYMin.value = cfg.axes.rotY.min
    rotYMax.value = cfg.axes.rotY.max
    rotZMin.value = cfg.axes.rotZ.min
    rotZMax.value = cfg.axes.rotZ.max

    // position initiale à la borne min
    rotX.value = rotXMin.value
    rotY.value = rotYMin.value
    rotZ.value = rotZMin.value
  } catch (e) {
    console.warn('Impossible de charger la config rotation', e)
  }
}

// --- unified drag setup using Pointer Events ---
function setupDrag(el: HTMLElement, onMove: (e: PointerEvent) => void) {
  const onPointerMove = (e: PointerEvent) => {
    const rect = el.parentElement!.getBoundingClientRect()
    onMove(e)
  }
  const onPointerUp = () => {
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)
  }
  el.addEventListener('pointerdown', (e: PointerEvent) => {
    e.preventDefault()
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', onPointerUp)
  })
}

function setupDragX() {
  const el = rectXSel.value!
  const parent = rectXBtn.value!
  setupDrag(el, e => {
    const rect = parent.getBoundingClientRect()
    const rawPct = (e.clientX - rect.left) / rect.width
    const pct = clamp(rawPct, 0, 1)
    rotX.value = rotXMin.value + pct * (rotXMax.value - rotXMin.value)
  })
}

function setupDragY() {
  const el = rectYSel.value!
  const parent = rectYBtn.value!
  setupDrag(el, e => {
    const rect = parent.getBoundingClientRect()
    const rawPct = (e.clientY - rect.top) / rect.height
    const pct = clamp(rawPct, 0, 1)
    rotY.value = rotYMin.value + pct * (rotYMax.value - rotYMin.value)
  })
}

function setupDragZ() {
  const el = document.querySelector('.circle-button > .rect-selector') as HTMLElement
  const parent = document.querySelector('.circle-button') as HTMLElement
  setupDrag(el, e => {
    const rect = parent.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    const dx = e.clientX - cx
    const dy = e.clientY - cy
    const angleDeg = ((Math.atan2(dy, dx) * 180) / Math.PI + 360) % 360
    const pct = angleDeg / 360
    rotZ.value = rotZMin.value + pct * (rotZMax.value - rotZMin.value)
  })
}

let roX: ReturnType<typeof useResizeObserver>
let roY: ReturnType<typeof useResizeObserver>

onMounted(() => {
  intervalId = window.setInterval(sendModule2, 100)
  void loadConfig()

  const measure = () => {
    if (rectXBtn.value) parentWidthX.value = rectXBtn.value.clientWidth
    if (rectXSel.value) selectorWidth.value = rectXSel.value.offsetWidth
    if (rectYBtn.value) parentHeightY.value = rectYBtn.value.clientHeight
    if (rectYSel.value) selectorHeight.value = rectYSel.value.offsetHeight
  }
  measure()
  if (rectXBtn.value) roX = useResizeObserver(rectXBtn, measure)
  if (rectYBtn.value) roY = useResizeObserver(rectYBtn, measure)

  setupDragX()
  setupDragY()
  setupDragZ()
})

onBeforeUnmount(() => {
  roX?.stop()
  roY?.stop()
})

onUnmounted(() => {
  if (intervalId !== null) clearInterval(intervalId)
})
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

.rect-selector {
  touch-action: none;
}
</style>

<style scoped src="~/assets/modules/2/style.css"></style>
