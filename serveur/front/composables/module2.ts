// File: serveur/front/composables/module2.ts
import * as THREE from 'three'
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import type { Ref } from 'vue'
import { onBeforeUnmount, onMounted } from 'vue'
import { useArtineo } from './useArtineo'

export default function useModule2(canvasRef: Ref<HTMLCanvasElement | null>) {
  // Guard SSR : rien à faire côté serveur
  if (!process.client) {
    return
  }

  const artClient = useArtineo(2)
  let loadedObject: THREE.Object3D | null = null
  let animationFrameId: number | null = null
  let pollingInterval: ReturnType<typeof setInterval> | null = null
  let isSubscribed = false

  function applyBuffer(buf: any) {
    if (!loadedObject) return
    if (typeof buf.rotX === 'number') loadedObject.rotation.x = buf.rotX
    if (typeof buf.rotY === 'number') loadedObject.rotation.y = buf.rotY
    if (typeof buf.rotZ === 'number') loadedObject.rotation.z = buf.rotZ
  }

  function setupWebsocketListener() {
    artClient.onMessage((msg: any) => {
      if (msg.action === 'get_buffer' && msg.buffer) {
        applyBuffer(msg.buffer)
      }
    })
  }

  function startPolling(intervalMs: number) {
    pollingInterval = setInterval(() => {
      artClient.getBuffer()
        .then(buf => applyBuffer(buf))
        .catch(() => {
          // ignore les erreurs réseau éventuelles
        })
    }, intervalMs)
  }

  function stopPolling() {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      pollingInterval = null
    }
  }

  function initThree(canvas: HTMLCanvasElement) {
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(
      60,
      canvas.clientWidth / canvas.clientHeight,
      0.1,
      1000
    )
    camera.position.set(0, 0, 4)
    camera.lookAt(0, 0, 0)

    const renderer = new THREE.WebGLRenderer({ antialias: true, canvas })
    renderer.setSize(canvas.clientWidth, canvas.clientHeight)

    const ambient = new THREE.AmbientLight(0xffffff, 1)
    scene.add(ambient)
    const dirLight = new THREE.SpotLight(0xffffff, 450)
    dirLight.angle = Math.PI / 3; // cone angle
    dirLight.position.set(0, 0, 5)
    scene.add(dirLight)

    const mtlLoader = new MTLLoader()
    mtlLoader.setPath('/models/module2/')
    mtlLoader.load(
      'Enter a title.mtl',
      materials => {
        materials.preload()
        const objLoader = new OBJLoader()
        objLoader.setMaterials(materials)
        objLoader.setPath('/models/module2/')
        objLoader.load(
          'Enter a title.obj',
          object => {
            const bbox = new THREE.Box3().setFromObject(object)
            const center = new THREE.Vector3()
            bbox.getCenter(center)

            const container = new THREE.Group()
            object.position.sub(center)
            container.add(object)

            scene.add(container)
            loadedObject = container
          },
          undefined,
          err => console.error('Erreur OBJ :', err)
        )
      },
      undefined,
      err => console.error('Erreur MTL :', err)
    )

    window.addEventListener('resize', () => {
      camera.aspect = canvas.clientWidth / canvas.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(canvas.clientWidth, canvas.clientHeight)
    })

    function animate() {
      animationFrameId = requestAnimationFrame(animate)
      renderer.render(scene, camera)
    }
    animate()
  }

  onMounted(async () => {
    const canvas = canvasRef.value
    if (!canvas) return

    initThree(canvas)

    // 1) Abonnement WebSocket (une seule fois)
    if (!isSubscribed) {
      isSubscribed = true
      setupWebsocketListener()

      // 2) Récupération initiale du buffer
      artClient.getBuffer()
        .then(buf => applyBuffer(buf))
        .catch(() => {
          // ignore
        })

      // 3) Récupérer le fps depuis la config
      let fps = 0
      try {
        const cfg = await artClient.fetchConfig()
        if (typeof cfg.fps === 'number' && cfg.fps > 0) {
          fps = Math.floor(cfg.fps)
          console.log(`[Module2] FPS configuré : ${fps}`)
        }
      } catch (e) {
        console.warn('[Module2] fetchConfig error', e)
      }

      // 4) Calculer intervalle : si fps invalide, on prend 20 FPS (50 ms)
      const intervalMs = fps > 0 ? Math.round(1000 / fps) : 50
      startPolling(intervalMs)
    }
  })

  onBeforeUnmount(() => {
    // Arrêt du rendu
    if (animationFrameId !== null) {
      cancelAnimationFrame(animationFrameId)
      animationFrameId = null
    }
    // Arrêt du polling
    stopPolling()
    // Pas de artClient.close() ici, car WS peut être partagé
  })
}
