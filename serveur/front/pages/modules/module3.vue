<template>
  <div class="page-3rfid">
    <div class="painting-frame-with-shadow">
      <div class="painting-frame">
        <div class="painting-container">
          <img v-if="backgroundUrl" :src="backgroundUrl" alt="painting" class="painting" />
        </div>
      </div>
    </div>

    <ArtyPlayer ref="player3" :module="3" @ready="onPlayerReady" class="arty-player" />

    <section class="choices">
      <button v-for="(label, i) in blobTexts" :key="i" class="choice-wrapper">
        <span class="choice" :class="[stateClasses[i], pressedStates[i] && 'pressed']">
          {{ label }}
        </span>
      </button>
    </section>

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
import { ref, watch, computed } from 'vue'
import ArtyPlayer from '~/components/ArtyPlayer.vue'
import useModule3 from '~/composables/module3.ts'

// 🟢 Étape courante
const step = ref(1)

const images = import.meta.glob(
  '~/assets/modules/3/steps/*.png',
  { eager: true, as: 'url' }
) as Record<string, string>

// URL de la step courante
const stepSrc = computed(() => {
  const entry = Object.entries(images)
    .find(([path]) => path.endsWith(`step${step.value}.png`))
  return entry ? entry[1] : ''
})

const player3 = ref<InstanceType<typeof ArtyPlayer> | null>(null)

const {
  backgroundSet,
  blobTexts,
  stateClasses,
  pressedStates,
  backgroundUrl,
  timerText,       // Ref<string>
  timerColor,
  startTimer
} = useModule3(player3)

// Quand le player est prêt, on lance l’intro
function onPlayerReady() {
  console.log('[Module3] ArtyPlayer prêt → lecture de l’intro…')
  player3.value?.playByTitle(
    'Jeu3.webm',
    () => console.log('→ début de Jeu3.webm'),
    startTimer
  )
}

// ✅ Condition prête : timer à "0:00" ET toutes les classes contiennent "correct"
const readyForNext = computed(() => {
  return timerText?.value === '0:00'
    && stateClasses.value.every(cls => cls.includes('correct'))
})

// 🔔 Watch sur readyForNext pour lancer la vidéo de fin une fois
watch(
  [() => timerText?.value, () => stateClasses.value],
  ([newTimer, newStates], [oldTimer, oldStates]) => {
    console.log('[Module3] timer:', newTimer, ' states:', newStates)
    if (
      newTimer === '0:00' ||
      newStates.every(s => s.includes('correct'))
    ) {
      console.log('[Module3] conditions OK → lecture de fin')
      player3.value?.playByTitle('Jeu3Fin.webm')
    }
  }
)
</script>

<style scoped src="~/assets/modules/3/style.css"></style>
