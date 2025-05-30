<template>
  <div class="page-3rfid">
    <img
      v-if="backgroundUrl"
      :src="backgroundUrl"
      alt="painting"
      class="painting"
    />

    <section class="choices">
      <button
        v-for="(label, i) in blobTexts"
        :key="i"
        class="choice-wrapper"
      >
        <!--
          On applique désormais :
          • stateClasses[i] pour la couleur (correct/wrong)
          • pressedStates[i] pour l’effet “enfoncé”
        -->
        <span
          class="choice"
          :class="[ stateClasses[i], pressedStates[i] && 'pressed' ]"
        >
          {{ label }}
        </span>
      </button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { useRuntimeConfig } from '#app'
import { computed } from 'vue'
import useModule3 from '~/composables/module3.ts'

definePageMeta({ layout: 'module' })

const { backgroundSet, blobTexts, stateClasses, pressedStates } = useModule3()
const { public: { apiUrl } } = useRuntimeConfig()

const backgroundUrl = computed(
  () => `${apiUrl}/getAsset?module=3&path=tableau${backgroundSet.value}.png`
)
</script>

<style scoped src="~/assets/modules/3/style.css"></style>
