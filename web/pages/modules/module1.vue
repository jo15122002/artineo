<template>
  <div class="module1-container">
    <img
      v-if="backgroundPath"
      :src="`${apiBase}/getAsset?module=1&path=${backgroundPath}`"
      class="fullscreen-img"
      :style="{ filter: filterStyle }"
    />
  </div>
</template>
  
  <script setup>
  import { useRuntimeConfig } from '#app'
import use1ir from '~/composables/module1'
  
  definePageMeta({ layout: 'module' })
  
  const { public: { apiBase } } = useRuntimeConfig()
  const { backgroundPath, filterStyle } = use1ir()
  </script>
  
  <style scoped src="~/assets/modules/1/style.css"></style>
  