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
import { ref } from 'vue'
import ArtyPlayer from '~/components/ArtyPlayer.vue'
import useModule3 from '~/composables/module3.ts'

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

const player3 = ref<InstanceType<typeof ArtyPlayer> | null>(null)

const {
  backgroundSet,
  blobTexts,
  stateClasses,
  pressedStates,
  backgroundUrl,
  timerText,
  timerColor
} = useModule3(player3)

function onPlayerReady() {
  console.log('[Module3] ArtyPlayer prêt → lecture de l’intro…')
  player3.value?.playByTitle(
    'imagination.mp4',
    () => console.log('→ onStart video imagination.mp4'),
    () => console.log('→ onComplete video imagination.mp4')
  )

  player3.value?.playByTitle(
    'Introduction.mp3',
    () => console.log('→ onStart audio Introduction.mp3'),
    () => console.log('→ onComplete audio Introduction.mp3')
  )
}
</script>

<style scoped src="~/assets/modules/3/style.css"></style>
