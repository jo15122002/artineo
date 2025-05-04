<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

// Récupère l'URL de base depuis runtimeConfig
const { public: { apiBase } } = useRuntimeConfig()

interface HealthCheckResponse {
  modules: Record<string, string>
}

// Lance immédiatement une première requête
const { data, refresh } = await useFetch<HealthCheckResponse>(
  `${apiBase}/hc`
)

let intervalId: ReturnType<typeof setInterval>

// Ne démarre le timer qu’une fois monté côté client
onMounted(() => {
  intervalId = setInterval(() => {
    refresh()
  }, 5000)
})

// Nettoie à la destruction du composant
onBeforeUnmount(() => {
  clearInterval(intervalId)
})
</script>


<template>
  <div>
    <h1>Dashboard</h1>
    <div v-for="(status, moduleId) in data.modules" :key="moduleId">
      <!-- ActivityOverview est auto-importé depuis components/activity/overview.vue -->
      <ActivityOverview :activity-status="status" />
    </div>
  </div>
</template>

<style scoped>
h1 {
  margin-bottom: 1.5rem;
}
</style>
