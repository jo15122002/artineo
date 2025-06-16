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

    startTimer()
    
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
      camera.position.set(0, -0.30, 2)

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

  // 8) Couleur du timer
      const TIMER_DURATION = 60 // secondes
      const timerSeconds = ref<number>(TIMER_DURATION)
      let timerInterval: number | undefined = undefined
  
        function startTimer() {
          // réinitialise la valeur et stoppe un éventuel timer en cours
          if (timerInterval) {
            clearInterval(timerInterval)
          }
          timerSeconds.value = TIMER_DURATION
          // décrémente chaque seconde
          timerInterval = window.setInterval(() => {
            // on décompte et on s'assure de ne pas passer sous 0
            timerSeconds.value = Math.max(timerSeconds.value - 1, 0)
            if (timerSeconds.value === 0 && timerInterval) {
              clearInterval(timerInterval)
            }
          }, 1000)
        }
  
      function hexToRgb(hex: string) {
        const h = hex.replace('#','')
        const bigint = parseInt(h, 16)
        return {
          r: (bigint >> 16) & 0xFF,
          g: (bigint >> 8)  & 0xFF,
          b:  bigint        & 0xFF,
        }
      }
      function rgbToHex(r: number, g: number, b: number) {
        const hr = r.toString(16).padStart(2, '0')
        const hg = g.toString(16).padStart(2, '0')
        const hb = b.toString(16).padStart(2, '0')
        return `#${hr}${hg}${hb}`
      }
      function lerp(a: number, b: number, t: number) {
        return a + (b - a) * t
      }
  
      const colorStops = [
          { p: 1.0, color: '#2626FF' },
          { p: 0.6, color: '#FA81C3' },
          { p: 0.3, color: '#FA4923' }
        ] as const
      
      const timerColor = computed(() => {
        // ratio entre 0 et 1
        const pct = timerSeconds.value / TIMER_DURATION
        // on parcourt chaque segment [i]→[i+1]
        for (let i = 0; i < colorStops.length - 1; i++) {
          const { p: p0, color: c0 } = colorStops[i]
          const { p: p1, color: c1 } = colorStops[i+1]
          if (pct <= p0 && pct >= p1) {
            // t = 0 à p0  → couleur c0
            // t = 1 à p1  → couleur c1
            const t = (p0 - pct) / (p0 - p1)
            const rgb0 = hexToRgb(c0)
            const rgb1 = hexToRgb(c1)
            const r = Math.round(lerp(rgb0.r, rgb1.r, t))
            const g = Math.round(lerp(rgb0.g, rgb1.g, t))
            const b = Math.round(lerp(rgb0.b, rgb1.b, t))
            return rgbToHex(r, g, b)
          }
        }
        // fallback
        return colorStops[colorStops.length - 1].color
      })
  
      // computed pour formater en M:SS
      const timerText = computed(() => {
        const m = Math.floor(timerSeconds.value / 60);
        const s = timerSeconds.value % 60;
        return `${m}:${String(s).padStart(2, '0')}`;
      });

  onBeforeUnmount(() => {
    if (pollingInterval) clearInterval(pollingInterval)
  })

  // 5️⃣ Expose les valeurs de rotation
  return { rotX, rotY, rotZ, timerColor, timerText }
}
