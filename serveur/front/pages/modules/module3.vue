<template>
  <div class="page-3rfid">
    <!-- fond dynamique -->
    <div
      id="background"
      class="background"
      :style="{ backgroundImage: `url(${backgroundUrl})` }"
    ></div>

    <!-- vidéo -->
    <video
      ref="videoRef"
      class="overlay-video"
      src="/AnimCadre.webm"
      muted
      playsinline
      webkit-playsinline
      preload="auto"
      @ended="onVideoEnded"
    ></video>

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
import { computed, ref, onMounted } from 'vue'
import { useRuntimeConfig } from '#app'
import useModule3 from '~/composables/module3.ts'

definePageMeta({ layout: 'module' })

const { public: { apiUrl } } = useRuntimeConfig()
const { backgroundSet, blobTexts, blobColors } = useModule3()
const videoRef = ref<HTMLVideoElement|null>(null)

// URL du fond
const backgroundUrl = computed(
  () => `${apiUrl}/getAsset?module=3&path=tableau${backgroundSet.value}.png`
)

function onVideoEnded() {
  const blobs = document.querySelectorAll('.blob')
  blobs.forEach(el => el.classList.add('fade-out'))
  videoRef.value?.classList.add('fade-out')
}

onMounted(async () => {
  try {
    await videoRef.value?.play()
  } catch {
    console.warn('Lecture automatique impossible')
  }
})
</script>

<style scoped src="~/assets/modules/3/style.css"></style>
