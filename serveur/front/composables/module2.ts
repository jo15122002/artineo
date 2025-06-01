// front/composables/module2.ts
import * as THREE from 'three'
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import type { Ref } from 'vue'
import { onBeforeUnmount, onMounted } from 'vue'
import { useArtineo } from './useArtineo'

export default function useModule2(canvasRef: Ref<HTMLCanvasElement | null>) {
  const artClient = useArtineo(2)
  let loadedObject: THREE.Object3D | null = null
  let intervalId: ReturnType<typeof setInterval> | null = null
  let animationFrameId: number | null = null

  function applyBuffer(buf: any) {
    if   (buf.rotX !== undefined && loadedObject) loadedObject.rotation.x = buf.rotX
    if   (buf.rotY !== undefined && loadedObject) loadedObject.rotation.y = buf.rotY
    if   (buf.rotZ !== undefined && loadedObject) loadedObject.rotation.z = buf.rotZ
  }

  async function pollBuffer() {
    try {
      const buf = await artClient.getBuffer()
      applyBuffer(buf)
    } catch { /* ignore */ }
  }

  function setupWebsocketListener() {
    artClient.onMessage((msg: any) => {
      if (msg.action === 'get_buffer' && msg.buffer) {
        applyBuffer(msg.buffer)
      }
    })
  }

  function initThree(canvas: HTMLCanvasElement) {
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(
      60,
      canvas.clientWidth / canvas.clientHeight,
      0.1,
      1000
    )
    camera.position.set(0, 0, 5)
    camera.lookAt(0, 0, 0)

    const renderer = new THREE.WebGLRenderer({ antialias: true, canvas })
    renderer.setSize(canvas.clientWidth, canvas.clientHeight)

    const ambient = new THREE.AmbientLight(0xffffff, 0.8)
    scene.add(ambient)
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.5)
    dirLight.position.set(5, 10, 7.5)
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
            object.scale.set(0.5, 0.5, 0.5)
            scene.add(object)
            loadedObject = object
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
      if (loadedObject) {
        // rotation appliquée par applyBuffer déjà mise à jour
      }
      renderer.render(scene, camera)
    }
    animate()
  }

  onMounted(() => {
    const canvas = canvasRef.value
    if (!canvas) return

    initThree(canvas)
    setupWebsocketListener()
    pollBuffer()
    intervalId = setInterval(pollBuffer, Math.round(1000 / 24))
  })

  onBeforeUnmount(() => {
    if (intervalId !== null) clearInterval(intervalId)
    if (animationFrameId !== null) cancelAnimationFrame(animationFrameId)
    artClient.close()
  })
}
