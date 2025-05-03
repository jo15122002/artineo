<template>
    <div class="page-3rfid">
      <div id="blob1" class="blob"/>
      <div id="blob2" class="blob"/>
      <div id="blob3" class="blob"/>
    </div>
  </template>
  
  <script setup>
  import { onMounted } from 'vue'
import use3rfid from '~/composables/module3'
  
  definePageMeta({
    layout: 'module'
  })
  
  // Démarre la logique du module au montage
  onMounted(() => {
    use3rfid()
  })
  </script>
  
  <style scoped src="~/assets/modules/3/style.css"></style>
  