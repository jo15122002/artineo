<template>
    <div class="page-3rfid">
      <div id="background"></div>

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

      <div id="blob1" class="blob"/>
      <div id="blob2" class="blob"/>
      <div id="blob3" class="blob"/>
    </div>
  </template>
  
  <script setup>
  import { onMounted, ref } from 'vue'
import use3rfid from '~/composables/module3'

  const videoRef = ref(null)
  
  definePageMeta({
    layout: 'module'
  })

  function onVideoEnded() {
    console.log('Vidéo terminée')
    if (videoRef.value) {
      const blobs = document.querySelectorAll('.blob')
      blobs.forEach((blob) => {
        blob.classList.add('fade-out')
      })
      videoRef.value.classList.add('fade-out')
    }
  }
  
  // Démarre la logique du module au montage
  onMounted(async () => {
    console.log('Module 3 démarré')
    use3rfid()

    if (videoRef.value) {
      try {
        await videoRef.value.play()
        console.log('Vidéo lancée automatiquement 🎥')
      } catch (err) {
        console.warn('Impossible de lancer la vidéo automatique :', err)
      }
    }
  })
  </script>
  
  <style scoped src="~/assets/modules/3/style.css"></style>
  