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

  // Applique au modèle les valeurs reçues dans le buffer
  function applyBuffer(buf: any) {
    if (!loadedObject) return
    if (typeof buf.rotX === 'number') loadedObject.rotation.x = buf.rotX
    if (typeof buf.rotY === 'number') loadedObject.rotation.y = buf.rotY
    if (typeof buf.rotZ === 'number') loadedObject.rotation.z = buf.rotZ
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

    // Lumières basiques
    const ambient = new THREE.AmbientLight(0xffffff, 0.8)
    scene.add(ambient)
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.5)
    dirLight.position.set(5, 10, 7.5)
    scene.add(dirLight)

    // Chargement MTL puis OBJ
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
            // 1) On recalcule le box du modèle pour trouver son centre
            const bbox = new THREE.Box3().setFromObject(object)
            const center = new THREE.Vector3()
            bbox.getCenter(center)

            // 2) On crée un container pour recentrer le modèle
            const container = new THREE.Group()
            // 2a) On décale l’objet afin que son centre devienne (0,0,0)
            object.position.sub(center)
            // 2b) On ajoute l’objet dans le container
            container.add(object)

            // 3) On ajoute ensuite ce container à la scène
            scene.add(container)

            loadedObject = container  // on fait tourner le container plutôt que l’objet brut
            //    → le container est déjà centré sur l’origine
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

    // Boucle d’animation
    function animate() {
      animationFrameId = requestAnimationFrame(animate)
      // Pas besoin de repositionner ici : on applique la rotation via applyBuffer
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
    intervalId = setInterval(pollBuffer, Math.round(1000 / 20)) // 20 FPS
  })

  onBeforeUnmount(() => {
    if (intervalId !== null) clearInterval(intervalId)
    if (animationFrameId !== null) cancelAnimationFrame(animationFrameId)
    artClient.close()
  })
}
