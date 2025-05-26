<template>
  <div class="page-3rfid">
    <img :src="backgroundUrl" alt="painting" class="painting" />

    <section class="choices">
      <button
        v-for="(label, i) in blobTexts"
        :key="i"
        :class="['choice-wrapper', stateClasses[i]]"
      >
        <span class="choice" :class="pressed && 'pressed'">
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

const { public: { apiUrl } } = useRuntimeConfig()
const { backgroundSet, blobTexts, stateClasses, pressed } = useModule3()

const backgroundUrl = computed(
  () => `${apiUrl}/getAsset?module=3&path=tableau${backgroundSet.value}.png`
)
</script>

<style scoped src="~/assets/modules/3/style.css"></style>
