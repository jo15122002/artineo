<template>
  <div class="module1-container">
    <div class="painting-frame-with-shadow">
      <div class="painting-frame">
        <div class="painting-container">
          <img v-if="backgroundPath" :src="`${apiUrl}/getAsset?module=1&path=${backgroundPath}`" class="fullscreen-img"
            :style="{ filter: filterStyle }" />
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
      <img v-if="!tutorialFinished" :src="stepSrc" alt="Indication step" class="indication-step" />
    </div>

    <!-- Zone cible (si debug=true) -->
    <div v-if="showDebug" class="debug-zone" :style="zoneStyle"></div>

    <!-- Cercle de détection IR (si debug=true) -->
    <div v-if="showDebug" class="debug-circle" :style="circleStyle"></div>
  </div>
</template>

<script setup lang="ts">
import { useRuntimeConfig } from '#app'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import useModule1 from '~/composables/module1.ts'

definePageMeta({ layout: 'module' })

const { public: { apiUrl } } = useRuntimeConfig()
const {
  backgroundPath,
  filterStyle,
  x, y,
  diamPx,
  timerColor,
  timerText
} = useModule1()

// 🟢 Étape courante
const step = ref(1)

// --- 1) variables pour la détection de step ---
const initialPos = reactive({ x: 0, y: 0, d: 0 })
const entryTimeStep = ref<number | null>(null)
const STEP_HOLD_TIME = 2 // secondes à tenir

// --- 2) fonctions de validation par étape ---
const conditionFns: Array<(cur: { x: number; y: number; d: number }) => boolean> = [
  cur => cur.d > initialPos.d,   // 1 - avancer (diamPx augmente → z avance)
  cur => cur.x > initialPos.x,   // 2 - vers la droite
  cur => cur.y > initialPos.y,   // 3 - vers le bas
  cur => cur.y < initialPos.y,   // 4 - vers le haut
  cur => cur.x < initialPos.x,   // 5 - vers la gauche
  cur => cur.d < initialPos.d    // 6 - reculer (diamPx diminue → z recule)
]

// images pour chaque step
const images = import.meta.glob(
  '~/assets/modules/1/steps/*.png',
  { eager: true, as: 'url' }
) as Record<string, string>

// nombre total d'étapes
const maxStep = Object.entries(images).length

// flag pour marquer la fin du tuto
const tutorialFinished = ref(false)

// 🔄 Computed pour retourner l'URL correspondant à la step courante
const stepSrc = computed(() => {
  const entry = Object.entries(images)
    .find(([path]) => path.endsWith(`step${step.value}.png`))
  return entry ? entry[1] : ''
})

// debug flag
const showDebug = ref(false)

// reactive pour la position cible (uniquement utile en debug)
const goodResponsePosition = reactive({ x: 0, y: 0 })
const goodResponseZoneSize = 30

onMounted(() => {
  const params = new URLSearchParams(window.location.search)
  showDebug.value = params.get('debug') === 'true' || params.get('debug') === '1'

  // initialisation aléatoire pour le debug
  goodResponsePosition.x = Math.random() * 320
  goodResponsePosition.y = Math.random() * 240

  // mémoriser la position de départ pour la step 1
  initialPos.x = x.value
  initialPos.y = y.value
  initialPos.d = diamPx.value
})

// --- 3) watcher : valide la step si la condition tient STEP_HOLD_TIME secondes ---
watch([x, y, diamPx], ([nx, ny, nd]) => {
  if (tutorialFinished.value) return
  if (step.value > conditionFns.length) return

  const now = performance.now() / 1000
  const isOk = conditionFns[step.value - 1]({ x: nx, y: ny, d: nd })

  if (isOk) {
    if (entryTimeStep.value === null) {
      entryTimeStep.value = now
    } else if (now - entryTimeStep.value >= STEP_HOLD_TIME) {
      // validation de la step
      step.value++
      // réinitialisation pour la prochaine étape
      initialPos.x = nx
      initialPos.y = ny
      initialPos.d = nd
      entryTimeStep.value = null
    }
  } else {
    // reset si condition rompue
    entryTimeStep.value = null
  }
})

// --- 4) watcher : termine le tuto quand on dépasse le nombre d'images ---
watch(step, (newStep) => {
  if (newStep > maxStep) {
    tutorialFinished.value = true
  }
})


// ────────────────────────────────────────────────────────────────────────────
// Styles debug
// ────────────────────────────────────────────────────────────────────────────

// style de la zone cible
const zoneStyle = computed(() => ({
  position: 'absolute',
  left: `${(goodResponsePosition.x / 320) * 100}%`,
  top: `${(goodResponsePosition.y / 240) * 100}%`,
  width: `${goodResponseZoneSize * 2}px`,
  height: `${goodResponseZoneSize * 2}px`,
  border: '2px dashed red',
  borderRadius: '50%',
  transform: 'translate(-50%, -50%)',
  pointerEvents: 'none',
  boxSizing: 'border-box',
  zIndex: 10
}))

// style du cercle IR
const circleStyle = computed(() => ({
  position: 'absolute',
  left: `${(x.value / 320) * 100}%`,
  top: `${(y.value / 240) * 100}%`,
  width: `${diamPx.value}px`,
  height: `${diamPx.value}px`,
  border: '2px solid red',
  borderRadius: '50%',
  transform: 'translate(-50%, -50%)',
  pointerEvents: 'none',
  boxSizing: 'border-box',
  zIndex: 11
}))
</script>

<style scoped src="~/assets/modules/1/style.css"></style>
