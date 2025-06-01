// front/composables/module2.ts
import * as THREE from 'three'
import { Ref, onBeforeUnmount, onMounted } from 'vue'
import { useArtineo } from './useArtineo'

/**
 * Composable pour Module 2 :
 * - initialise Three.js (scene, caméra fixe, renderer, cube)
 * - récupère périodiquement le buffer Artineo (via getBuffer) ou se souscrit à onMessage
 * - applique les valeurs reçues sur la rotation du cube
 */
export default function useModule2(canvasRef: Ref<HTMLCanvasElement | null>) {
  // 1) Préparer le client Artineo
  const moduleId = 2
  const artClient = useArtineo(moduleId)

  // 2) Variables Three.js
  let scene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.WebGLRenderer
  let cube: THREE.Mesh
  let animationFrameId: number | null = null
  let pollIntervalId: ReturnType<typeof setInterval> | null = null

  // -- Fonction d'initialisation Three.js --
  function initThree(canvas: HTMLCanvasElement) {
    // a) Scène
    scene = new THREE.Scene()

    // b) Caméra fixe
    const fov = 60
    const aspect = canvas.clientWidth / canvas.clientHeight
    const near = 0.1
    const far = 1000
    camera = new THREE.PerspectiveCamera(fov, aspect, near, far)
    camera.position.set(0, 0, 5)
    camera.lookAt(0, 0, 0)

    // c) Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true, canvas })
    renderer.setSize(canvas.clientWidth, canvas.clientHeight)

    // d) Cube de test (géométrie + matériau)
    const geometry = new THREE.BoxGeometry(1, 1, 1)
    const material = new THREE.MeshNormalMaterial()
    cube = new THREE.Mesh(geometry, material)
    scene.add(cube)

    // e) Gérer le redimensionnement
    window.addEventListener('resize', onWindowResize)
  }

  // -- Callback resize --
  function onWindowResize() {
    const canvas = canvasRef.value!
    camera.aspect = canvas.clientWidth / canvas.clientHeight
    camera.updateProjectionMatrix()
    renderer.setSize(canvas.clientWidth, canvas.clientHeight)
  }

  // -- Boucle d’animation (render) --
  function animate() {
    animationFrameId = requestAnimationFrame(animate)
    renderer.render(scene, camera)
  }

  // -- Met à jour la rotation du cube à partir du buffer reçu --
  function applyBufferToCube(buf: any) {
    // Exemples de champs possibles dans buf :
    //   { rotX: <nombre>, rotY: <nombre>, rotZ: <nombre> }
    // Si vous avez dans votre back-end des champs différents, adaptez-les ici.
    if (typeof buf.rotX === 'number') cube.rotation.x = buf.rotX
    if (typeof buf.rotY === 'number') cube.rotation.y = buf.rotY
    if (typeof buf.rotZ === 'number') cube.rotation.z = buf.rotZ
    // Si votre buffer contient d’autres données (par exemple un angle unique),
    // mappez-les de la manière souhaitée :
    //   cube.rotation.y = buf.angle * Math.PI / 180
  }

  // -- Récupération périodique du buffer (fallback HTTP polling) --
  async function pollBuffer() {
    try {
      const buf = await artClient.getBuffer()
      applyBufferToCube(buf)
    } catch {
      // Ignore si erreur réseau
    }
  }

  // -- Subcription WebSocket :
  //   à chaque message { action: 'get_buffer', buffer: {...} },
  //   on applique la rotation directement.  --
  function setupWebsocketListener() {
    artClient.onMessage((msg: any) => {
      if (msg.action === 'get_buffer' && msg.buffer) {
        applyBufferToCube(msg.buffer)
      }
      // Vous pouvez aussi vérifier msg.module si besoin
    })
  }

  // -- Démarrage du composable --
  onMounted(() => {
    const canvas = canvasRef.value
    if (!canvas) return

    // 1) Initialiser Three.js
    initThree(canvas)
    animate()

    // 2) Se connecter (ou démarrer automatiquement) au WebSocket Artineo
    //   Le composable useArtineo() se charge de la connexion sous-jacente.
    setupWebsocketListener()

    // 3) Faire un premier getBuffer() en HTTP (fallback)
    pollBuffer()
    // 4) Puis réitérer toutes les 100 ms (par exemple) pour rattraper les cas où 
    //    WebSocket n’atteint pas le client
    pollIntervalId = setInterval(pollBuffer, 100)
  })

  // -- Nettoyage à la destruction du composable --
  onBeforeUnmount(() => {
    if (animationFrameId !== null) {
      cancelAnimationFrame(animationFrameId)
      animationFrameId = null
    }
    if (pollIntervalId !== null) {
      clearInterval(pollIntervalId)
      pollIntervalId = null
    }
    window.removeEventListener('resize', onWindowResize)
    artClient.close()
    // Optionnel : renderer.dispose(), géométries.dispose(), matériaux.dispose()
  })
}
