<template>
  <div class="module2-page">
    <div class="controls module2-controls">
      <div v-show="currentAxis === 'x'">
        <div class="button rectX-button" ref="rectXBtn">
          <img src="~/assets/modules/2/rectX.svg" alt="Slider X" />
          <!-- On pilote désormais l’axe X en déplacement vertical -->
          <div class="rect-selector" ref="rectXSel" :style="{ '--t-y': translateX + 'px' }" />
        </div>
      </div>
      <div>
        <div v-show="currentAxis === 'y'" class="button rectY-button" ref="rectYBtn">
          <img src="~/assets/modules/2/rectY.svg" alt="Slider Y" />
          <!-- On pilote désormais l’axe Y en déplacement horizontal -->
          <div class="rect-selector" ref="rectYSel" :style="{ '--t-x': translateY + 'px' }" />
        </div>
      </div>
      <div v-show="currentAxis === 'z'">
        <div class="button circle-button" :class="{ gray: !isXChecked || !isYChecked }">
          <img src="~/assets/modules/2/circle.svg" alt="Knob Z" />
          <div class="rect-selector" :style="{ transform: `rotate(${rotZDeg}deg) translateY(-115px)` }" />
        </div>
      </div>

      <img src="~/assets/modules/2/splash-check.png" alt="splash check" class="splash-check"
        :style="{ opacity: opacityCheckMark }" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { clamp } from '@antfu/utils'
import { useResizeObserver } from '@vueuse/core'
import { computed, onBeforeUnmount, onMounted, onUnmounted, ref } from 'vue'
import { useArtineo } from '~/composables/useArtineo'

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
const startToAppearCheckMarkTolerance = 1.5
const objectiveRotX = 2
const objectiveRotY = 1
const objectiveRotZ = 0.5
const isXChecked = computed(() => Math.abs(rotX.value - objectiveRotX) < tolerance)
const isYChecked = computed(() => Math.abs(rotY.value - objectiveRotY) < tolerance)
const isZChecked = computed(() => Math.abs(rotZ.value - objectiveRotZ) < tolerance)

const currentAxis = ref<'x' | 'y' | 'z'>('x')

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
    // on utilise maintenant l'axe Y pour X
    const rawPct = (e.clientY - rect.top) / rect.height
    const pct = clamp(rawPct, 0, 1)
    rotX.value = rotXMin.value + pct * (rotXMax.value - rotXMin.value)
  })
}

function setupDragY() {
  const el = rectYSel.value!
  const parent = rectYBtn.value!
  setupDrag(el, e => {
    const rect = parent.getBoundingClientRect()
    // on utilise maintenant l'axe X pour Y
    const rawPct = (e.clientX - rect.left) / rect.width
    const pct = clamp(rawPct, 0, 1)
    rotY.value = rotYMin.value + pct * (rotYMax.value - rotYMin.value)
  })
}

function setupDragZ() {
  const el = document.querySelector('.circle-button > .rect-selector') as HTMLElement
  const parent = document.querySelector('.circle-button') as HTMLElement
  setupDrag(el, e => {
    const rect = parent.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    const angle = Math.atan2(e.clientY - centerY, e.clientX - centerX)
    const pct = (angle + Math.PI / 2) / (2 * Math.PI) // Normalize to [0, 1]
    rotZ.value = rotZMin.value + pct * (rotZMax.value - rotZMin.value)
  })
}

let roX: ReturnType<typeof useResizeObserver>
let roY: ReturnType<typeof useResizeObserver>

const opacityCheckMark = ref(0)

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

  setInterval(() => {
    let opacity = opacityCheckMark.value
    if ((currentAxis.value === 'x' && isXChecked.value) || (currentAxis.value === 'y' && isYChecked.value) || (currentAxis.value === 'z' && isZChecked.value)) {
      opacity += 0.02 * (Math.pow(opacityCheckMark.value, 2) + 1)
    } else {
      opacity -= 0.02 * (Math.pow(opacityCheckMark.value, 2) + 1)
    }
    opacityCheckMark.value = Math.max(0, Math.min(1, opacity))
    if (opacityCheckMark.value === 1) {
      setTimeout(() => {
        if (currentAxis.value === 'x' && isXChecked.value) {
          currentAxis.value = 'y'
        } else if (currentAxis.value === 'y' && isYChecked.value) {
          currentAxis.value = 'z'
        }
        opacityCheckMark.value = 0
      }, 500)
    }
  }, 50)

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

<style>
body,
html {
  height: 100%;
  width: 100%;
  margin: auto;
  padding: 0;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>

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
  display: flex;
  flex-direction: column;
  align-items: center;
}

.module2-controls {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.rect-selector {
  touch-action: none;
}
</style>

<style scoped src="~/assets/modules/2/style.css"></style>
