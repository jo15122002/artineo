<template>
  <div class="module2-container">
    <canvas ref="canvas" />
  </div>
</template>

<script setup lang="ts">
import * as THREE from 'three'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useArtineo } from '~/composables/useArtineo'
// Importer les loaders OBJ/MTL
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'

definePageMeta({ layout: 'module' })

// 1) Réf vers le <canvas>
const canvas = ref<HTMLCanvasElement | null>(null)

// 2) Client Artineo pour le module 2
const artClient = useArtineo(2)

// 3) Trois refs pour les angles de rotation
const rotX = ref(0)
const rotY = ref(0)
const rotZ = ref(0)

// 4) Paramètres de fréquence de récupération (24 FPS)
const FPS = 24
const intervalMs = Math.round(1000 / FPS)
let intervalId: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  // 1) Écoute passive d’éventuels messages WS “get_buffer”
  artClient.onMessage(msg => {
    if (msg.action === 'get_buffer' && msg.buffer) {
      const buf = msg.buffer as Record<string, any>
      if (typeof buf.rotX === 'number') rotX.value = buf.rotX
      if (typeof buf.rotY === 'number') rotY.value = buf.rotY
      if (typeof buf.rotZ === 'number') rotZ.value = buf.rotZ
    }
  })

  // 2) Démarrage du polling WS à 24 FPS
  intervalId = setInterval(() => {
    artClient.getBuffer()
      .then(buf => {
        if (typeof buf.rotX === 'number') rotX.value = buf.rotX
        if (typeof buf.rotY === 'number') rotY.value = buf.rotY
        if (typeof buf.rotZ === 'number') rotZ.value = buf.rotZ
      })
      .catch(() => {
        // Ignorer les erreurs (ex. WS non dispo)
      })
  }, intervalMs)

  // 3) Initialisation Three.js
  if (!canvas.value) return

  const renderer = new THREE.WebGLRenderer({
    canvas: canvas.value,
    antialias: true
  })
  // On adapte la taille du renderer à celle du canvas DOM
  const width = canvas.value.clientWidth
  const height = canvas.value.clientHeight
  renderer.setSize(width, height)

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000)
  camera.position.z = 5

  // 4) Point lumineux pour mieux voir le modèle
  const ambient = new THREE.AmbientLight(0xffffff, 0.8)
  scene.add(ambient)
  const dirLight = new THREE.DirectionalLight(0xffffff, 0.5)
  dirLight.position.set(5, 10, 7.5)
  scene.add(dirLight)

  // 5) Chargement du .mtl puis du .obj
  const mtlLoader = new MTLLoader()
  // On indique le chemin d’accès relatif aux fichiers placés dans public/models/monObjet/
  mtlLoader.setPath('/models/module2/')
  mtlLoader.load(
    'Enter a title.mtl',
    materials => {
      materials.preload()
      // Une fois que le .mtl est chargé, on configure l’OBJLoader
      const objLoader = new OBJLoader()
      objLoader.setMaterials(materials)
      objLoader.setPath('/models/module2/')
      objLoader.load(
        'Enter a title.obj',
        object => {
          // On peut éventuellement ajuster l’échelle/position
          object.scale.set(0.5, 0.5, 0.5)   // exemple : réduire de moitié
          object.position.set(0, 0, 0)

          scene.add(object)

          // On conserve la référence pour animer la rotation
          // en fermant sur le scope parent:
          loadedObject = object
        },
        undefined,
        err => {
          console.error('Erreur chargement OBJ :', err)
        }
      )
    },
    undefined,
    err => {
      console.error('Erreur chargement MTL :', err)
    }
  )

  // Référence pour l’objet chargé (sera défini dans le loader)
  let loadedObject: THREE.Object3D | null = null

  // 6) Boucle d’animation
  function animate() {
    requestAnimationFrame(animate)
    if (loadedObject) {
      loadedObject.rotation.x = rotX.value
      loadedObject.rotation.y = rotY.value
      loadedObject.rotation.z = rotZ.value
    }
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
