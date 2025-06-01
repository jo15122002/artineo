<template>
  <div class="module2-container">
    <canvas ref="canvas" />
  </div>
</template>

<script setup lang="ts">
import * as THREE from 'three'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useArtineo } from '~/composables/useArtineo'

definePageMeta({ layout: 'module' })

// Réf vers le <canvas>
const canvas = ref<HTMLCanvasElement | null>(null)

// Client Artineo pour le module 2
const artClient = useArtineo(2)

// Trois refs pour les angles de rotation
const rotX = ref(0)
const rotY = ref(0)
const rotZ = ref(0)

// Nombre d’images par seconde pour la récupération du buffer
const FPS = 24
const intervalMs = Math.round(1000 / FPS)
let intervalId: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  // 1) WebSocket : on écoute les push “get_buffer” si jamais le serveur envoie spontanément
  artClient.onMessage(msg => {
    if (msg.action === 'get_buffer' && msg.buffer) {
      const buf = msg.buffer as Record<string, any>
      if (typeof buf.rotX === 'number') rotX.value = buf.rotX
      if (typeof buf.rotY === 'number') rotY.value = buf.rotY
      if (typeof buf.rotZ === 'number') rotZ.value = buf.rotZ
    }
  })

  // 2) Démarrage d’un timer à FPS pour appeler getBuffer() via WS
  intervalId = setInterval(() => {
    artClient.getBuffer()
      .then(buf => {
        if (typeof buf.rotX === 'number') rotX.value = buf.rotX
        if (typeof buf.rotY === 'number') rotY.value = buf.rotY
        if (typeof buf.rotZ === 'number') rotZ.value = buf.rotZ
      })
      .catch(() => {
        // ignore si échec
      })
  }, intervalMs)

  // 3) Initialisation de Three.js dans le canvas
  if (!canvas.value) return

  const renderer = new THREE.WebGLRenderer({
    canvas: canvas.value,
    antialias: true
  })
  // Adapter la taille du renderer à celle du canvas DOM
  const width = canvas.value.clientWidth
  const height = canvas.value.clientHeight
  renderer.setSize(width, height)

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000)
  camera.position.z = 5

  const geometry = new THREE.BoxGeometry()
  const material = new THREE.MeshNormalMaterial()
  const cube = new THREE.Mesh(geometry, material)
  scene.add(cube)

  function animate() {
    requestAnimationFrame(animate)
    // Appliquer les valeurs actuelles reçues
    cube.rotation.x = rotX.value
    cube.rotation.y = rotY.value
    cube.rotation.z = rotZ.value
    renderer.render(scene, camera)
  }
  animate()
})

onBeforeUnmount(() => {
  if (intervalId !== null) {
    clearInterval(intervalId)
    intervalId = null
  }
})
</script>

<style scoped src="~/assets/modules/2/style.css"></style>
