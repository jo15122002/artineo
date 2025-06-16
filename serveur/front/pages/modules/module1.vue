<template>
  <div class="module1-container">
    <div class="painting-frame-with-shadow">
      <div class="painting-frame">
        <div class="painting-container">
          <img v-if="backgroundPath" :src="`${apiUrl}/getAsset?module=1&path=${backgroundPath}`" class="fullscreen-img"
            :style="{ filter: filterStyle }" />
        </div>
      </div>
    </div>

    <div class="timer" :style="{ '--timer-color': timerColor }">
      <div class="timer-splat"></div>
      <span class="timer-text">{{ timerText }}</span>
    </div>

    <div class="arty">
      <!-- image fixe -->
      <img src="~/assets/modules/4/images/arty.png" alt="Arty" class="arty-img" />

      <!-- image dynamique -->
      <img v-if="!tutorialFinished" :src="stepSrc" alt="Indication step" class="indication-step" />
      <ArtyPlayer ref="player1" :module="1" @ready="onPlayerReady" class="arty-player" />
      <ArtyPlayer ref="playerFrame" :module="1" @ready="console.log(`ply frame ready`)" class="arty-player" />
      <ArtyPlayer ref="artyFrame" :module="1" @ready="console.log(`ply arty ready`)" class="arty-player" />
    </div>

    <!-- Zone cible (si debug=true) -->
    <div v-if="showDebug" class="debug-zone" :style="zoneStyle"></div>

    <!-- Cercle de détection IR (si debug=true) -->
    <div v-if="showDebug" class="debug-circle" :style="circleStyle"></div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import ArtyPlayer from '~/components/ArtyPlayer.vue'
import useModule1 from '~/composables/module1.ts'

const { x, y, diamPx } = useModule1()

// 1) liste des directions dans l’ordre ou aléatoirement
const directions = ['Avance', 'Droite', 'Recule', 'Gauche']
const currentIndex = ref(0)
const currentDir = () => directions[currentIndex.value]

// 2) refs vers les deux players de hint
const playerFrame = ref<InstanceType<typeof ArtyPlayer> | null>(null)
const playerArty = ref<InstanceType<typeof ArtyPlayer> | null>(null)

// 3) délais (en ms)
const hintDelay = 3000   // 3s avant la video simple
const artyHintDelay = 2000   // 2s après la simple avant la version arty

let hintTimer: number | null = null
let artyHintTimer: number | null = null

function clearHintTimers() {
  if (hintTimer != null) { clearTimeout(hintTimer); hintTimer = null }
  if (artyHintTimer != null) { clearTimeout(artyHintTimer); artyHintTimer = null }
}

function startHintTimers() {
  clearHintTimers()
  // 3a) timer pour la video simple
  hintTimer = window.setTimeout(() => {
    playerFrame.value?.playByTitle(`${currentDir()}.webm`)
    // 3b) puis timer pour la video arty
    artyHintTimer = window.setTimeout(() => {
      playerArty.value?.playByTitle(`${currentDir()}_Arty.webm`)
    }, artyHintDelay)
  }, hintDelay)
}

// 4) fonction qui valide la direction courante
function checkDirection(cur: { x: number, y: number, d: number }) {
  const init = initialPos
  switch (currentDir()) {
    case 'Avance': return cur.d > init.d
    case 'Recule': return cur.d < init.d
    case 'Droite': return cur.x > init.x
    case 'Gauche': return cur.x < init.x
  }
  return false
}

// onMounted : on mémorise la position de départ et on lance le premier hint
const initialPos = { x: 0, y: 0, d: 0 }
onMounted(() => {
  initialPos.x = x.value
  initialPos.y = y.value
  initialPos.d = diamPx.value
  startHintTimers()
})

// 5) on watch la position pour détecter la bonne direction
watch([x, y, diamPx], ([nx, ny, nd]) => {
  const cur = { x: nx, y: ny, d: nd }
  if (checkDirection(cur)) {
    // on a validé la consigne
    clearHintTimers()
    // préparation de la prochaine
    initialPos.x = nx
    initialPos.y = ny
    initialPos.d = nd
    currentIndex.value++
    if (currentIndex.value < directions.length) {
      startHintTimers()
    } else {
      // fin de tuto…
    }
  }
})
</script>

<style scoped src="~/assets/modules/1/style.css"></style>
