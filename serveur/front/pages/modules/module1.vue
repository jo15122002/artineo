<template>
  <div class="module1-container">
    <!-- Cadre et fond -->
    <div class="painting-frame-with-shadow">
      <div class="painting-frame">
        <div class="painting-container">
          <img v-if="backgroundPath" :src="`${apiUrl}/getAsset?module=1&path=${backgroundPath}`" class="fullscreen-img"
            :style="{ filter: filterStyle }" />
        </div>
      </div>
    </div>

    <!-- Timer -->
    <div class="timer" :style="{ '--timer-color': timerColor }">
      <div class="timer-splat"></div>
      <span class="timer-text">{{ timerText }}</span>
    </div>

    <!-- Hints vidéos -->
    <div class="arty">
      <ArtyPlayer ref="fullScreenPlayer" :module="1" @ready="onFullScreenPlayerReady" class="arty-player" />
      <ArtyPlayer ref="playerFrame" :module="1" @ready="console.log('playerFrame prêt')" class="arty-player" />
      <ArtyPlayer ref="playerArty" :module="1" @ready="console.log('playerArty prêt')" class="arty-player" />
    </div>

    <!-- Optionnel : affichage textuel de l'indice courant -->
    <!-- <div v-if="currentDirection" class="indication-text">
      Indice : {{ currentDirection }}
    </div> -->

    <!-- Debug zones -->
    <div v-if="showDebug" class="debug-zone" :style="zoneStyle"></div>
    <div v-if="showDebug" class="debug-circle" :style="circleStyle"></div>
  </div>
</template>

<script setup lang="ts">
import { useRuntimeConfig } from '#app'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import ArtyPlayer from '~/components/ArtyPlayer.vue'
import useModule1 from '~/composables/module1.ts'

definePageMeta({ layout: 'module' })

// → Runtime + capteurs
const { public: { apiUrl } } = useRuntimeConfig()
const {
  backgroundPath,
  filterStyle,
  x, y,
  diamPx,
  timerColor,
  timerText,
  responseAlreadyValidated,
  resetTimer,
  resumeTimer
} = useModule1()

// → 1) Indice courant (mis à jour par la logique de jeu)
const currentDirection = ref<null | 'Avance' | 'Droite' | 'Gauche' | 'Recule'>(null)

// → 2) Position de départ pour comparer le mouvement
const initialPos = reactive({ x: 0, y: 0, d: 0 })

// → 3) Refs vers les deux lecteurs de hint
const playerFrame = ref<InstanceType<typeof ArtyPlayer> | null>(null)
const playerArty = ref<InstanceType<typeof ArtyPlayer> | null>(null)
const fullScreenPlayer = ref<InstanceType<typeof ArtyPlayer> | null>(null)

const canPoll = ref(false)

function onFullScreenPlayerReady() {
  fullScreenPlayer.value?.playByTitle('intro.mp4',
    () => resetTimer(),
    () => {
      resumeTimer()
      console.log('Full screen player ended')
      console.log("canpoll", canPoll.value)
      canPoll.value = true
    })
}

// → 4) Délai avant affichage des hints (en ms)
const hintDelay = 3000
let hintTimer: number | null = null

const showTipX = ref(false)
const showTipY = ref(false)
const showTipZone = ref(false)
const timeoutshowTipX = ref<ReturnType<typeof setTimeout>>()
const timeoutshowTipY = ref<ReturnType<typeof setTimeout>>()
const timeoutshowTipZone = ref<ReturnType<typeof setTimeout>>()
const showTipDelay = 3000

function clearHintTimers() {
  if (hintTimer != null) {
    clearTimeout(hintTimer)
    hintTimer = null
  }
}

function startHintTimer() {
  clearHintTimers()
  hintTimer = window.setTimeout(() => {
    if (!currentDirection.value) return
    // Lancer les deux vidéos en simultané
    playerFrame.value?.playByTitle(`${currentDirection.value}.webm`)
    playerArty.value?.playByTitle(`${currentDirection.value}_Arty.webm`, undefined, undefined, "arty-left")
  }, hintDelay)
}

// → 5) Vérification du mouvement correct
function isMovingCorrectly(cur: { x: number; y: number; d: number }) {
  if (!currentDirection.value) return false
  switch (currentDirection.value) {
    case 'Avance': return cur.d > initialPos.d
    case 'Recule': return cur.d < initialPos.d
    case 'Droite': return cur.x > initialPos.x
    case 'Gauche': return cur.x < initialPos.x
  }
}

// → 6) À chaque nouvelle direction, on réinitialise la référence
watch(currentDirection, (dir) => {
  if (!dir) return
  initialPos.x = x.value
  initialPos.y = y.value
  initialPos.d = diamPx.value
  // startHintTimer()
})

const XruleToShowTip = 40
const YruleToShowTip = 40
const diamRuleToShowTip = 20

// → 7) On observe les capteurs et on annule les hints dès réussite
watch([x, y, diamPx], ([nx, ny, nd]) => {
  // console.log("canPoll", canPoll.value, "x", nx, "y", ny, "diamPx", nd)
  if (!canPoll.value || responseAlreadyValidated) return
  const cur = { x: nx, y: ny, d: nd }
  if (isMovingCorrectly(cur)) {
    clearHintTimers()
    // la logique de jeu doit ensuite mettre à jour `currentDirection`
  }
  if (showTipX.value || showTipY.value || showTipZone.value) return;
  if (nx > goodResponsePosition.x + XruleToShowTip ||
    nx < goodResponsePosition.x - XruleToShowTip) {
    console.log('showTipX', nx, goodResponsePosition.x, XruleToShowTip)
    if (!timeoutshowTipX.value) {
      timeoutshowTipX.value = setTimeout(() => {
        showTipX.value = true
        timeoutshowTipX.value = undefined;
      }, showTipDelay)
    }
  } else {
    clearTimeout(timeoutshowTipX.value)
    timeoutshowTipX.value = undefined;
  }
  // if (ny > goodResponsePosition.y + YruleToShowTip ||
  //   ny < goodResponsePosition.y - YruleToShowTip) {
  //   if (!timeoutshowTipY.value) {
  //     timeoutshowTipY.value = setTimeout(() => {
  //       showTipY.value = true
  //       clearTimeout(timeoutshowTipY.value)
  //     }, showTipDelay)
  //   }
  // } else {
  //   clearTimeout(timeoutshowTipY.value)
  // }
  if (nd > goodResponseZoneSize + diamRuleToShowTip ||
    nd < goodResponseZoneSize - diamRuleToShowTip) {
    console.log('showTipZone', nd, goodResponseZoneSize, diamRuleToShowTip)
    if (!timeoutshowTipZone.value) {
      console.log('showTipZone démarré')
      timeoutshowTipZone.value = setTimeout(() => {
        console.log('showTipZone déclenché')
        showTipZone.value = true
        timeoutshowTipZone.value = undefined;
      }, showTipDelay)
    }
  } else {
    clearTimeout(timeoutshowTipZone.value)
    timeoutshowTipZone.value = undefined;
  }
})

watch([showTipX, showTipY, showTipZone], () => {
  console.log("canPoll", canPoll.value, "showTipX", showTipX.value, "showTipY", showTipY.value, "showTipZone", showTipZone.value)
  if (!canPoll.value || responseAlreadyValidated) return
  if (showTipX.value) {
    console.log('showTipX', x.value, goodResponsePosition.x)
    playerFrame.value?.playByTitle(x.value > goodResponsePosition.x ? 'Gauche.webm' : 'Droite.webm', undefined, () => {
      console.log('showTipX terminé')
      showTipX.value = false
    })
    playerArty.value?.playByTitle(x.value > goodResponsePosition.x ? 'Gauche_Arty.webm' : 'Droite_Arty.webm')
    showTipY.value = showTipZone.value = false
    // } else if (showTipY.value) {
    //   playerFrame.value?.playByTitle(y.value > goodResponsePosition.y ? 'Haut.webm' : 'Bas.webm', undefined, () => {
    //   showTipY.value = false
    // })
    //   playerArty.value?.playByTitle(y.value > goodResponsePosition.y ? 'Haut_Arty.webm' : 'Bas_Arty.webm')
    //   showTipX.value = showTipZone.value = false
  } else if (showTipZone.value) {
    console.log('showTipZone', diamPx.value, goodResponseZoneSize)
    playerFrame.value?.playByTitle(diamPx.value > goodResponseZoneSize ? 'Recule.webm' : 'Avance.webm', undefined, () => {
      console.log('showTipZone terminé')
      showTipZone.value = false
    })
    playerArty.value?.playByTitle(diamPx.value > goodResponseZoneSize ? 'Recule_Arty.webm' : 'Avance_Arty.webm')
    showTipX.value = showTipY.value = false
  }
})

watch(() => responseAlreadyValidated, (val) => {
  if (val) {
    fullScreenPlayer.value?.playByTitle('fin.mp4')
  }
})

// → Debug
const showDebug = ref(false)
const goodResponsePosition = reactive({ x: 0, y: 0 })
const goodResponseZoneSize = 30

onMounted(() => {
  const params = new URLSearchParams(window.location.search)
  showDebug.value = params.get('debug') === 'true' || params.get('debug') === '1'

  // position aléatoire pour debug
  goodResponsePosition.x = Math.random() * 320
  goodResponsePosition.y = Math.random() * 240

  // init position de référence
  initialPos.x = x.value
  initialPos.y = y.value
  initialPos.d = diamPx.value

  // exemple : démarrer la première consigne
  currentDirection.value = 'Avance'
})

// Styles debug
const zoneStyle = computed(() => ({
  position: 'absolute',
  left: `${(goodResponsePosition.x / 320) * 100}%`,
  top: `${(goodResponsePosition.y / 240) * 100}%`,
  width: `${goodResponseZoneSize * 2}px`,
  height: `${goodResponseZoneSize * 2}px`,
  border: '2px dashed red',
  borderRadius: '50%',
  transform: 'translate(-50%, -50%)',
  pointerEvents: 'none',
  boxSizing: 'border-box',
  zIndex: 10
}))
const circleStyle = computed(() => ({
  position: 'absolute',
  left: `${(x.value / 320) * 100}%`,
  top: `${(y.value / 240) * 100}%`,
  width: `${diamPx.value}px`,
  height: `${diamPx.value}px`,
  border: '2px solid red',
  borderRadius: '50%',
  transform: 'translate(-50%, -50%)',
  pointerEvents: 'none',
  boxSizing: 'border-box',
  zIndex: 11
}))
</script>

<style scoped src="~/assets/modules/1/style.css"></style>
