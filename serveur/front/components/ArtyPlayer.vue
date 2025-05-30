<template>
    <div class="arty-player">
        <div ref="container" class="arty-container"></div>
        <div class="controls" v-if="mediaList.length">
            <button @click="prev" :disabled="currentIndex === 0">‹ Prev</button>
            <button @click="play">Play</button>
            <button @click="next" :disabled="currentIndex + 1 >= mediaList.length">Next ›</button>
            <span>{{ mediaList[currentIndex].title }}</span>
        </div>
        <p v-else>Pas de média pour ce module.</p>
    </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useArtyManager } from '~/composables/useArtyManager';

const props = defineProps<{ module: number }>()
const container = ref<HTMLElement | null>(null)

const { load, play, next, prev, mediaList, currentIndex } =
    useArtyManager(props.module, container.value)

onMounted(async () => {
    // on attend le rendu pour récupérer `container.value`
    await load()
})
</script>

<style scoped>
.arty-container {
    width: 100%;
    max-height: 60vh;
    margin-bottom: 0.5rem;
}

.controls {
    display: flex;
    gap: .5rem;
    align-items: center;
}
</style>
