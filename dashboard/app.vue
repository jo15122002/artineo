<script setup lang="ts">
const runtimeConfig = useRuntimeConfig()

interface HealthCheckResponse {
  modules: any[]
}

// Fetching healthcheck data from the API every 5 seconds
const { data, refresh } = await useFetch<HealthCheckResponse>(runtimeConfig.public.apiUrl + ':' + runtimeConfig.public.apiPort + '/hc')

// Set up a timer to refresh the data every 5 seconds
const interval = setInterval(() => {
  refresh()
}, 5000)

// Clear the interval when the component is unmounted
onBeforeUnmount(() => {
  clearInterval(interval)
})
</script>

<template>
  <div>
    <h1>Dashboard</h1>
    <div v-for="(item, index) in data.modules" :key="index">
      <ActivityOverview :activity-status="item" />
    </div>
  </div>
</template>
