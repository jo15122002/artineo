<!-- components/ArtyPlayer.vue -->
<template>
    <div class="arty-player">
        <!-- Container pour <audio> ou <video> -->
        <div ref="container" class="arty-container" v-show="!isAudio"></div>

        <!-- Contrôles visibles seulement si c’est une vidéo (isAudio=false) -->
        <div class="controls" v-if="!isAudio && mediaList.length">
            <button @click="prev" :disabled="currentIndex === 0">‹ Prev</button>
            <button @click="play">Play</button>
            <button @click="next" :disabled="currentIndex + 1 >= mediaList.length">Next ›</button>
            <span class="title">Actuel : {{ mediaList[currentIndex].title }}</span>
        </div>

        <!-- Message si aucun média -->
        <p v-if="!mediaList.length">Pas de média disponible pour ce module.</p>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, type Ref } from 'vue';
import { useArtyManager } from '~/composables/useArtyManager';

// 1) On déclare l’émission d’un événement `ready` dès que le player est opérationnel.
const emit = defineEmits<{
    (e: 'ready'): void
}>()

// 2) On reçoit la prop `module` pour savoir quel module interroger
const props = defineProps<{ module: number }>()

// 3) Réf du <div> dans lequel on injectera <audio> ou <video>
const container: Ref<HTMLElement | null> = ref(null)

// 4) Appel du composable en lui passant `container`
//    useArtyManager s’occupe de faire `load()` et `initPlayer()`
const arty = useArtyManager(props.module, container)

// 5) Dès que `container.value` existe, on appelle `arty.load()`
//    Puis, au bout de `arty.load()` + `initPlayer()`, on émettra `ready`.
watch(
    container,
    async (el) => {
        if (el) {
            console.log(`[ArtyPlayer] container monté pour module=${props.module}`)
            await arty.load()
            // À ce stade, la liste mediaList est chargée et initPlayer() a déjà été appelé
            // → on peut émettre l’événement `ready`
            console.log(`[ArtyPlayer] Émission de l’événement "ready" pour module=${props.module}`)
            emit('ready')
        }
    },
    { immediate: true }
)

// 6) Extraction des méthodes et refs depuis le composable
const { play, next, prev, playByTitle, mediaList, currentIndex } = arty

// 7) Computed qui indique si le média courant est un audio
const isAudio = computed(() => {
    if (!mediaList.value.length) return false
    return mediaList.value[currentIndex.value].type.startsWith('audio/')
})

// 8) Exposer `playByTitle` pour que le parent puisse l’appeler via <ArtyPlayer ref="player" …>
defineExpose({ playByTitle })
</script>

<style scoped>
.arty-container {
    width: 100%;
    max-height: 60vh;
    margin-bottom: 0.5rem;
}

/* Quand v-show="false", arty-container aura `display:none`, ce qui masque le player audio/vidéo */
.arty-container[style*="display: none"] {
    height: 0;
    overflow: hidden;
}

.controls {
    display: flex;
    gap: .5rem;
    align-items: center;
    flex-wrap: wrap;
}

.title {
    margin-left: 1rem;
    font-weight: bold;
}
</style>
