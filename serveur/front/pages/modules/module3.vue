<template>
  <div class="page-3rfid">
    <img v-if="backgroundUrl" :src="backgroundUrl" alt="painting" class="painting" />

    <!-- 
      On place le player ici, avec ref="player3"
    -->
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

// — 1) On crée le ref qui pointera vers l’instance ArtyPlayer —
const player3 = ref<InstanceType<typeof ArtyPlayer> | null>(null)

// — 2) On transmet player3 à notre composable —
const {
  backgroundSet,
  blobTexts,
  stateClasses,
  pressedStates,
  backgroundUrl,
  playIntro
} = useModule3(player3)

/**
 * Si vous avez configuré ArtyPlayer pour émettre `@ready="..."`, 
 * alors on peut écouter ici. Sinon, vous pouvez tout appeler à la main.
 */
function onPlayerReady() {
  console.log('[module3.vue] ArtyPlayer a émis ready → onPlayerReady()')
  // On peut déclencher directement la méthode du composable, qui à son tour
  // appellera player3.value!.playByTitle("Introduction.mp3")
  playIntro()
}

// Vous pouvez aussi appeler `playIntro()` plus tard, suite à un clic 3RFID, etc.

</script>

<style scoped src="~/assets/modules/3/style.css"></style>
