<template>
    <div class="module2-page">
        <h1>Module 2 – Simulation</h1>

        <div class="controls module2-controls">
            <label v-show="!isXChecked">
                rotX :
                <input type="range" v-model.number="module2Fields.rotX" :min="-6.28" :max="6.28" step="0.01" />
                <span>{{ module2Fields.rotX.toFixed(2) }}</span>
            </label>

            <label v-show="isXChecked && !isYChecked">
                rotY :
                <input type="range" v-model.number="module2Fields.rotY" :min="-6.28" :max="6.28" step="0.01" />
                <span>{{ module2Fields.rotY.toFixed(2) }}</span>
            </label>

            <label v-show="isYChecked && !isZChecked">
                rotZ :
                <input type="range" v-model.number="module2Fields.rotZ" :min="-6.28" :max="6.28" step="0.01" />
                <span>{{ module2Fields.rotZ.toFixed(2) }}</span>
            </label>
        </div>

        <div class="button-row">
            <button @click="sendModule2">Envoyer buffer</button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, reactive } from 'vue'
import { useArtineo } from '~/composables/useArtineo'

const module2Fields = reactive({
    rotX: 0,
    rotY: 0,
    rotZ: 0
})

const tolerance = 0.2 // tolérance pour les rotations
const objectiveRotX = 2
const objectiveRotY = 1
const objectiveRotZ = 0.5
const isXChecked = computed(() => Math.abs(module2Fields.rotX - objectiveRotX) < tolerance)
const isYChecked = computed(() => Math.abs(module2Fields.rotY - objectiveRotY) < tolerance)
const isZChecked = computed(() => Math.abs(module2Fields.rotZ - objectiveRotZ) < tolerance)

const client = useArtineo(2)
let intervalId: number | null = null

function sendModule2() {

    client.setBuffer({
        rotX: module2Fields.rotX,
        rotY: module2Fields.rotY,
        rotZ: module2Fields.rotZ,
        isXChecked: isXChecked.value,
        isYChecked: isYChecked.value,
        isZChecked: isZChecked.value
    })
}

onMounted(() => {
    // Envoi continu automatique toutes les 100 ms
    intervalId = window.setInterval(sendModule2, 100)
})

onUnmounted(() => {
    if (intervalId !== null) {
        clearInterval(intervalId)
    }
})
</script>

<style scoped>
@font-face {
    font-family: "CheeseSauce";
    src: url('./Cheese-Sauce.woff2') format("woff2");
}

.module2-page {
    padding: 2rem;
    font-family: "CheeseSauce", sans-serif;
    max-width: 400px;
    margin: auto;
}

.module2-controls label {
    display: flex;
    align-items: center;
    margin: 0.5rem 0;
}

.module2-controls input[type='range'] {
    margin: 0 0.5rem;
    flex: 1;
}

.module2-controls span {
    width: 60px;
    text-align: right;
    font-family: monospace;
}

.button-row {
    margin-top: 1rem;
}

.button-row button {
    padding: 0.5rem 1rem;
    font-size: 1rem;
    cursor: pointer;
}
</style>
