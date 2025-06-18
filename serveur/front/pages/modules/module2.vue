<template>
  <div class="module2-container">
    <div class="frame-and-buttons-wrapper">
      <div class="frame-shadow">
        <div class="frame">
          <canvas ref="canvas" />
        </div>
      </div>

      <ArtyPlayer ref="player2" :module="2" @ready="onPlayerReady" class="arty-player arty-angle"
        style="display: none" />
      <ArtyPlayer ref="player2Music" :module="2" @ready="onMusicPlayerReady" class="arty-player"
        style="display: none" />

      <div class="buttons-wrapper" ref="buttonsWrapper">

        <!-- Slider X -->
        <div class="slider-wrapper">
          <div class="button rectX-button" ref="rectXBtn">
            <img src="~/assets/modules/2/rectX.svg" alt="Slider X" />
            <div class="rect-selector" ref="rectXSel" :style="{ '--t-x': translateX + 'px' }" />
          </div>
          <img v-if="showXCheck" src="~/assets/modules/2/splash-check.png" alt="splash check" class="splash-check" />
        </div>


        <!-- Slider Y -->
        <div class="slider-wrapper">
          <div class="button rectY-button" ref="rectYBtn" :class="{ 'gray': !isXChecked }">
            <img src="~/assets/modules/2/rectY.svg" alt="Slider Y" />
            <div class="rect-selector" ref="rectYSel" :style="{ '--t-y': translateY + 'px' }" />
          </div>
          <img v-if="showYCheck" src="~/assets/modules/2/splash-check.png" alt="splash check" class="splash-check" />
        </div>

        <!-- Knob Z -->
        <div class="slider-wrapper">
          <div class="button circle-button" :class="{ 'gray': !isXChecked || !isYChecked }">
            <img src="~/assets/modules/2/circle.svg" alt="Knob Z" />
            <div class="rect-selector" :style="{ transform: `rotate(${rotZDeg}deg) translateY(-115px)` }" />
          </div>
          <img v-if="showZCheck" src="~/assets/modules/2/splash-check.png" alt="splash check" class="splash-check" />
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
import ArtyPlayer from '~/components/ArtyPlayer.vue'
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
  isXChecked, isYChecked, isZChecked,
  showXCheck, showYCheck, showZCheck,
  startTimer
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

const player2 = ref<InstanceType<typeof ArtyPlayer> | null>(null)
const player2Music = ref<InstanceType<typeof ArtyPlayer> | null>(null)

function onPlayerReady() {
  player2.value?.playByTitle(
    'Jeu2_intro.webm',
    () => console.log('→ début de Jeu2.webm'),
    () => startTimer?.()
  )
}

function onMusicPlayerReady() {
  player2Music.value?.playByTitle("song.wav")
}

let isAlreadyPlayed = false

watch(
  [isXChecked, isYChecked, isZChecked, timerText],
  ([xChecked, yChecked, zChecked, t]) => {
    if (((xChecked && yChecked && zChecked) || t === '0:00') && !isAlreadyPlayed) {
      // Lance la vidéo principale (mettre ici le titre de la vidéo désirée)
      isAlreadyPlayed = true
      setTimeout(() => {
        player2.value?.playByTitle(
          'Jeu2Fin.webm',
          () => console.log('→ lancement de la vidéo de fin'),
          () => player2Music.value?.stop()
        )
      }, 2000)
    }
  }
)

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
