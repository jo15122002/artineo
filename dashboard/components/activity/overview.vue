<script setup lang="ts">
defineProps<{
    activityStatus: string;
}>();
</script>
<template>
    <div class="activity-overview">
        <h1>Activity Overview {{ activityStatus }}</h1>
        <p>This is the activity overview component. yes very good</p>
    </div>
</template>