<template>
  <div class="page-3rfid">
    <!-- fond dynamique -->
    <div
      id="background"
      class="background"
      :style="{ backgroundImage: `url(${backgroundUrl})` }"
    ></div>

    <!-- 3 blobs générés dynamiquement -->
    <div
      v-for="i in 3"
      :key="i"
      :id="`blob${i}`"
      class="blob"
      :style="{ backgroundColor: blobColors[i-1] }"
    >
      <span>{{ blobTexts[i-1] }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRuntimeConfig } from '#app'
import { computed } from 'vue'
import useModule3 from '~/composables/module3.ts'

definePageMeta({ layout: 'module' })

const { public: { apiUrl } } = useRuntimeConfig()
const { backgroundSet, blobTexts, blobColors } = useModule3()

const backgroundUrl = computed(
  () => `${apiUrl}/getAsset?module=3&path=tableau${backgroundSet.value}.png`
)
</script>

<style scoped src="~/assets/modules/3/style.css"></style>
