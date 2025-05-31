<template>
  <div class="page-3rfid">
    <img v-if="backgroundUrl" :src="backgroundUrl" alt="painting" class="painting" />

    <ArtyPlayer ref="player3" :module="3" @ready="onPlayerReady" class="arty-player" />

    <section class="choices">
      <button v-for="(label, i) in blobTexts" :key="i" class="choice-wrapper">
        <span class="choice" :class="[stateClasses[i], pressedStates[i] && 'pressed']">
          {{ label }}
        </span>
      </button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ArtyPlayer from '~/components/ArtyPlayer.vue'
import useModule3 from '~/composables/module3.ts'

const player3 = ref<InstanceType<typeof ArtyPlayer> | null>(null)

const {
  backgroundSet,
  blobTexts,
  stateClasses,
  pressedStates,
  backgroundUrl
} = useModule3(player3)

function onPlayerReady() {
  console.log('[Module3] ArtyPlayer prêt → lecture de l’intro…')
  player3.value?.playByTitle(
    'Introduction.mp3',
    () => console.log('→ onStart : début de Introduction.mp3'),
    () => console.log('→ onComplete : fin de Introduction.mp3')
  )
}
</script>

<style scoped src="~/assets/modules/3/style.css"></style>
