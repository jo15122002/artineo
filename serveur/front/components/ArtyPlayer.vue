<!-- components/ArtyPlayer.vue -->
<template>
    <div class="arty-player">
        <!-- Container dans lequel on injectera dynamiquement <audio> ou <video> -->
        <div ref="container"></div>
    </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useArtyManager } from '~/composables/useArtyManager';

/**
 * Propriétés que reçoit ce composant : on lui passe simplement le moduleId.
 */
const props = defineProps<{
    module: number
}>()
const emit = defineEmits<{
    (e: 'ready'): void
}>()

// Réf vers le <div> container
const container = ref<HTMLElement | null>(null)

// On récupère l’API du composable (load(), play(), playByTitle(), etc.)
const {
    mediaList,
    currentIndex,
    load,         // ← on l’expose pour le parent
    play,
    next,
    prev,
    playByTitle
} = useArtyManager(props.module, container)

// On “premium expose” ces méthodes pour que le parent (module3.vue) y accède via `player3.value`
defineExpose({
    load,
    play,
    next,
    prev,
    playByTitle
})

// Dès que <div ref="container"> existe, on appelle load()
// et quand la promesse est résolue, on émet "ready".
watch(
    () => container.value,
    async (el) => {
        if (el) {
            await load()
            // Dès que la liste est chargée, on prévient le parent que tout est prêt.
            emit('ready')
        }
    },
    { immediate: true }
)
</script>

<style>
/* Styles pour la vidéo plein écran */
.arty-fullscreen-video {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    z-index: 10000;
    background-color: transparent;
}

#arty-left {
    position: absolute;
    left: 0;
    top: 0;
    width: 50%;
    height: auto;
}

/* Styles pour cacher l’audio */
.arty-audio-hidden {
    display: none;
}
</style>
