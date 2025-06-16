// File: serveur/front/composables/module2.ts
import * as THREE from 'three'
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import type { Ref } from 'vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useArtineo } from './useArtineo'

export default function useModule2(canvasRef: Ref<HTMLCanvasElement | null>) {
  if (!process.client) {
    const rotX = ref(0)
    const rotY = ref(0)
    const rotZ = ref(0)
    const timerColor = ref('#2626FF')
    const timerText = ref('1:00')
    return { rotX, rotY, rotZ, timerColor, timerText }
  }

  const artClient = useArtineo(2)

  // 1️⃣ Valeurs réactives de rotation
  const rotX = ref(0)
  const rotY = ref(0)
  const rotZ = ref(0)

  // 🚧 Bornes depuis la config
  const rotXMin = ref(-Infinity)
  const rotXMax = ref(+Infinity)
  const rotYMin = ref(-Infinity)
  const rotYMax = ref(+Infinity)
  const rotZMin = ref(-Infinity)
  const rotZMax = ref(+Infinity)

  // 2️⃣ Clamp utilitaire
  const clamp = (v: number, min: number, max: number) => Math.min(Math.max(v, min), max)

  // 3️⃣ Chargement des bornes depuis la config HTTP
  async function loadConfig() {
    try {
      const cfg = await artClient.fetchConfig()
      console.log('Config rotation chargée', cfg)
      rotXMin.value = cfg.axes.rotX.min ?? rotXMin.value
      rotXMax.value = cfg.axes.rotX.max ?? rotXMax.value
      rotYMin.value = cfg.axes.rotY.min ?? rotYMin.value
      rotYMax.value = cfg.axes.rotY.max ?? rotYMax.value
      rotZMin.value = cfg.axes.rotZ.min ?? rotZMin.value
      rotZMax.value = cfg.axes.rotZ.max ?? rotZMax.value

      console.log('Bornes de rotation appliquées', {
        rotXMin: rotXMin.value,
        rotXMax: rotXMax.value,
        rotYMin: rotYMin.value,
        rotYMax: rotYMax.value,
        rotZMin: rotZMin.value,
        rotZMax: rotZMax.value,
      })
    } catch (e) {
      console.warn('Impossible de charger la config rotation', e)
    }
  }

  // 4️⃣ Applique le clamp sur le buffer reçu
  function applyBuffer(buf: any) {
    console.log('Buffer reçu', buf)
    if (typeof buf.rotX === 'number')
      rotX.value = clamp(buf.rotX, rotXMin.value, rotXMax.value)
    if (typeof buf.rotY === 'number')
      rotY.value = clamp(buf.rotY, rotYMin.value, rotYMax.value)
    if (typeof buf.rotZ === 'number')
      rotZ.value = clamp(buf.rotZ, rotZMin.value, rotZMax.value)
    console.log('Valeurs de rotation appliquées', {
      rotX: rotX.value,
      rotY: rotY.value,
      rotZ: rotZ.value,
    })
  }

  let pollingInterval: ReturnType<typeof setInterval> | null = null

  // 5️⃣ Timer et couleurs
  const TIMER_DURATION = 60 // secondes
  const timerSeconds = ref<number>(TIMER_DURATION)
  let timerInterval: number | undefined

  function startTimer() {
    if (timerInterval) clearInterval(timerInterval)
    timerSeconds.value = TIMER_DURATION
    timerInterval = window.setInterval(() => {
      timerSeconds.value = Math.max(timerSeconds.value - 1, 0)
      if (timerSeconds.value === 0 && timerInterval) {
        clearInterval(timerInterval)
      }
    }, 1000)
  }

  function hexToRgb(hex: string) {
    const h = hex.replace('#', '')
    const bigint = parseInt(h, 16)
    return {
      r: (bigint >> 16) & 0xff,
      g: (bigint >> 8) & 0xff,
      b: bigint & 0xff,
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
    { p: 0.3, color: '#FA4923' },
  ] as const

  const timerColor = computed(() => {
    const pct = timerSeconds.value / TIMER_DURATION
    for (let i = 0; i < colorStops.length - 1; i++) {
      const { p: p0, color: c0 } = colorStops[i]
      const { p: p1, color: c1 } = colorStops[i + 1]
      if (pct <= p0 && pct >= p1) {
        const t = (p0 - pct) / (p0 - p1)
        const rgb0 = hexToRgb(c0)
        const rgb1 = hexToRgb(c1)
        const r = Math.round(lerp(rgb0.r, rgb1.r, t))
        const g = Math.round(lerp(rgb0.g, rgb1.g, t))
        const b = Math.round(lerp(rgb0.b, rgb1.b, t))
        return rgbToHex(r, g, b)
      }
    }
    return colorStops[colorStops.length - 1].color
  })

  const timerText = computed(() => {
    const m = Math.floor(timerSeconds.value / 60)
    const s = timerSeconds.value % 60
    return `${m}:${String(s).padStart(2, '0')}`
  })

  onMounted(async () => {
    // Charge d'abord les bornes de rotation
    await loadConfig()

    // Démarre le timer
    startTimer()

    // 6️⃣ WebSocket push
    artClient.onMessage((msg: any) => {
      if (msg.action === 'get_buffer' && msg.buffer) {
        applyBuffer(msg.buffer)
      }
    })

    // 7️⃣ Initial + HTTP fallback
    try {
      const buf0 = await artClient.getBuffer()
      applyBuffer(buf0)
    } catch {}

    // 8️⃣ Polling (20 FPS → 50 ms)
    const intervalMs = 50
    pollingInterval = setInterval(async () => {
      try {
        const buf = await artClient.getBuffer()
        applyBuffer(buf)
      } catch {}
    }, intervalMs)

    // —————— Three.js ——————
    const canvas = canvasRef.value
    if (canvas) {
      const scene = new THREE.Scene()
      const camera = new THREE.PerspectiveCamera(
        60,
        canvas.clientWidth / canvas.clientHeight,
        0.1,
        1000
      )
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
        .load('Enter a title.mtl', (materials) => {
          materials.preload()
          new OBJLoader()
            .setMaterials(materials)
            .setPath('/models/module2/')
            .load('Enter a title.obj', (object) => {
              const center = new THREE.Box3()
                .setFromObject(object)
                .getCenter(new THREE.Vector3())
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
    if (timerInterval) clearInterval(timerInterval)
  })

  return { rotX, rotY, rotZ, timerColor, timerText }
}
