<template>
  <div class="page-3rfid">
    <img v-if="backgroundUrl" :src="backgroundUrl" alt="painting" class="painting" />

    <!-- 
      On écoute `@ready="onPlayerReady"` : 
      dès que le composant ArtyPlayer émet "ready", on appelle onPlayerReady()
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
import { useRuntimeConfig } from '#app'
import { computed, ref } from 'vue'
import ArtyPlayer from '~/components/ArtyPlayer.vue'
import useModule3 from '~/composables/module3.ts'

definePageMeta({ layout: 'module' })

// 1) ref pour récupérer l’instance <ArtyPlayer>
const player3 = ref<InstanceType<typeof ArtyPlayer> | null>(null)

// 2) Fonction déclenchée à la réception de l’événement `ready`
const titreVoulu = 'Introduction.mp3'
function onPlayerReady() {
  console.log(`[Module 3] onPlayerReady() → lecture de "${titreVoulu}"`)
  // Appel en toute sécurité : l’enfant ArtyPlayer est monté et a chargé sa liste
  player3.value?.playByTitle(titreVoulu)
}

// 3) Reste du composant 3RFID
const { backgroundSet, blobTexts, stateClasses, pressedStates } = useModule3()
const { public: { apiUrl } } = useRuntimeConfig()

const backgroundUrl = computed(
  () => `${apiUrl}/getAsset?module=3&path=tableau${backgroundSet.value}.png`
)
</script>

<style scoped src="~/assets/modules/3/style.css"></style>

<style scoped>
.module3-player-wrapper {
  margin-top: 2rem;
  padding: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}
</style>
