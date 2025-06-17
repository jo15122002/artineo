<template>
  <div class="module4-container">

    <div class="arty">
      <ArtyPlayer ref="player4" :module="4" @ready="onPlayerReady" class="arty-player arty-angle" style="display: none" />
    </div>

    <div class="painting-frame-with-shadow">
      <div class="painting-frame">
        <div class="painting-container">
          <canvas ref="canvas" />
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
import { ref, computed, watch, onMounted } from 'vue'
import ArtyPlayer from '~/components/ArtyPlayer.vue'
import use4kinect from '~/composables/module4.ts'

definePageMeta({ layout: 'module' })

// --- 1. état et imports d’images ---
const step = ref(1)
const images = import.meta.glob(
  '~/assets/modules/4/images/steps/*.png',
  { eager: true, as: 'url' }
) as Record<string, string>
const stepSrc = computed(() => {
  const entry = Object.entries(images)
    .find(([path]) => path.endsWith(`step${step.value}.png`))
  return entry ? entry[1] : ''
})
const maxStep = Object.keys(images)
  .map(path => {
    const m = path.match(/step(\d+)\.png$/)
    return m ? +m[1] : 0
  })
  .reduce((a, b) => Math.max(a, b), 0)

// --- 2. canvas & composable Kinect ---
const canvas = ref<HTMLCanvasElement | null>(null)
const {
  strokes,
  objects,
  timerColor,
  timerText,
  timerSeconds,
  startTimer
} = use4kinect(canvas, step)

// --- 3. ArtyPlayer ref + helpers ---
const player4 = ref<InstanceType<typeof ArtyPlayer> | null>(null)

function playStepVideo(n: number) {
  player4.value?.playByTitle(
    `step${n}.webm`,
    /* onStart? */ undefined,
    /* onEnd */ () => {
      // une fois la vidéo finie, on démarre le timer
      startTimer?.()
    }
  )
}

function onPlayerReady() {
  // lancement de la vidéo du premier step
  playStepVideo(step.value)
}

// --- 4. à chaque changement de step, jouer la vidéo ---
watch(step, (newStep, oldStep) => {
  // évite de relancer celle du premier step deux fois si déjà lancée
  if (newStep !== oldStep) {
    playStepVideo(newStep)
  }
})

// --- 5. fin du timer : changer de step ou lancer l’outro ---
if (timerSeconds) {
  watch(timerSeconds, newVal => {
    if (newVal === 0) {
      if (step.value < maxStep) {
        // on passe au step suivant (watch(step) gérera la vidéo + timer)
        step.value++
      } else {
        // dernier step terminé → outroteur
        player4.value?.playByTitle('outro.webm')
      }
    }
  })
}

// --- 6. onMounted pour la taille du canvas ---
onMounted(() => {
  const ROISz = { w: 305, h: 200, scale: 3 }
  const c = canvas.value!
  c.width = ROISz.w * ROISz.scale
  c.height = ROISz.h * ROISz.scale
})
</script>

<style scoped src="~/assets/modules/4/style.css"></style>
