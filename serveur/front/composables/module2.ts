// File: serveur/front/composables/module2.ts
import * as THREE from 'three'
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import type { Ref } from 'vue'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useArtineo } from './useArtineo'

export default function useModule2(canvasRef: Ref<HTMLCanvasElement | null>) {
  if (!process.client) return { rotX: ref(0), rotY: ref(0), rotZ: ref(0) }

  const artClient = useArtineo(2)

  // 1️⃣ Valeurs réactives de rotation
  const rotX = ref(0)
  const rotY = ref(0)
  const rotZ = ref(0)

  let pollingInterval: ReturnType<typeof setInterval> | null = null

  function applyBuffer(buf: any) {
    if (typeof buf.rotX === 'number') rotX.value = buf.rotX
    if (typeof buf.rotY === 'number') rotY.value = buf.rotY
    if (typeof buf.rotZ === 'number') rotZ.value = buf.rotZ
  }

  onMounted(async () => {
    // 2️⃣ WebSocket push
    artClient.onMessage((msg: any) => {
      if (msg.action === 'get_buffer' && msg.buffer) {
        applyBuffer(msg.buffer)
      }
    })

    // 3️⃣ Initial + HTTP fallback
    try {
      const buf0 = await artClient.getBuffer()
      applyBuffer(buf0)
    } catch {}

    // 4️⃣ Polling selon fps (configurable), ici 20 FPS
    const intervalMs = 50
    pollingInterval = setInterval(() => {
      artClient.getBuffer()
        .then(applyBuffer)
        .catch(() => {})
    }, intervalMs)

    // —————— Three.js (inchangé) ——————
    const canvas = canvasRef.value
    if (canvas) {
      const scene = new THREE.Scene()
      const camera = new THREE.PerspectiveCamera(60, canvas.clientWidth / canvas.clientHeight, 0.1, 1000)
      camera.position.set(0, 0, 4)

      const renderer = new THREE.WebGLRenderer({ antialias: true, canvas })
      renderer.setSize(canvas.clientWidth, canvas.clientHeight)

      scene.add(new THREE.AmbientLight(0xffffff, 1))
      const dirLight = new THREE.SpotLight(0xffffff, 450)
      dirLight.angle = Math.PI / 3
      dirLight.position.set(0, 0, 5)
      scene.add(dirLight)

      let loadedObject: THREE.Object3D | null = null
      new MTLLoader()
        .setPath('/models/module2/')
        .load('Enter a title.mtl', materials => {
          materials.preload()
          new OBJLoader()
            .setMaterials(materials)
            .setPath('/models/module2/')
            .load('Enter a title.obj', object => {
              const center = new THREE.Box3().setFromObject(object).getCenter(new THREE.Vector3())
              const container = new THREE.Group()
              object.position.sub(center)
              container.add(object)
              scene.add(container)
              loadedObject = container
            })
        })

      function animate() {
        requestAnimationFrame(animate)
        if (loadedObject) {
          // Applique aussi la rotation 3D pour le modèle
          loadedObject.rotation.x = rotX.value
          loadedObject.rotation.y = rotY.value
          loadedObject.rotation.z = rotZ.value
        }
        renderer.render(scene, camera)
      }
      animate()
    }
  })

  onBeforeUnmount(() => {
    if (pollingInterval) clearInterval(pollingInterval)
  })

  // 5️⃣ Expose les valeurs de rotation
  return { rotX, rotY, rotZ }
}
