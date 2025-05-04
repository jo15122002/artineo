<script setup lang="ts">
defineProps<{
  activityStatus: string;
}>()
</script>

<template>
  <div class="activity-overview">
    <h2>Activity Overview {{ activityStatus }}</h2>
    <p>This is the activity overview component.</p>
  </div>
</template>

<style scoped>
.activity-overview {
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-bottom: 1rem;
}
</style>
