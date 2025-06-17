// File: serveur/front/composables/module2.ts
import * as THREE from 'three'
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js'
import type { Ref } from 'vue'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useArtineo } from './useArtineo'

export default function useModule2(canvasRef: Ref<HTMLCanvasElement | null>) {
  if (!process.client) {
    // mode SSR / build
    const zero = ref(0)
    const timerColor = ref('#2626FF')
    const timerText = ref('1:00')
    // on renvoie aussi des bornes neutres
    return {
      rotX: zero, rotY: zero, rotZ: zero,
      rotXMin: zero, rotXMax: zero,
      rotYMin: zero, rotYMax: zero,
      rotZMin: zero, rotZMax: zero,
      timerColor, timerText,
    }
  }

  const artClient = useArtineo(2)

  // rotations et bornes
  const rotX = ref(0)
  const rotY = ref(0)
  const rotZ = ref(0)
  const rotXMin = ref(-Infinity)
  const rotXMax = ref(+Infinity)
  const rotYMin = ref(-Infinity)
  const rotYMax = ref(+Infinity)
  const rotZMin = ref(-Infinity)
  const rotZMax = ref(+Infinity)

  const isXChecked: Ref<boolean> = ref(false)
  const isYChecked: Ref<boolean> = ref(false)
  const isZChecked: Ref<boolean> = ref(false)

  // clamp
  const clamp = (v: number, min: number, max: number) => Math.min(Math.max(v, min), max)

  // charge la config axes.rot? {min,max}
  async function loadConfig() {
    try {
      const cfg = await artClient.fetchConfig()
      // ex. { axes: { rotX: { min:…, max:… }, … } }
      rotXMin.value = cfg.axes.rotX.min  ?? rotXMin.value
      rotXMax.value = cfg.axes.rotX.max  ?? rotXMax.value
      rotYMin.value = cfg.axes.rotY.min  ?? rotYMin.value
      rotYMax.value = cfg.axes.rotY.max  ?? rotYMax.value
      rotZMin.value = cfg.axes.rotZ.min  ?? rotZMin.value
      rotZMax.value = cfg.axes.rotZ.max  ?? rotZMax.value
    } catch (e) {
      console.warn('Impossible de charger la config rotation', e)
    }
  }

  // applique et clamp
  function applyBuffer(buf: any) {
    if (!buf || typeof buf !== 'object' || buf.rotX === undefined) return
    if (typeof buf.rotX === 'number')
      rotX.value = clamp(buf.rotX, rotXMin.value, rotXMax.value)
      isXChecked.value = buf.isXChecked

    if (typeof buf.rotY === 'number')
      rotY.value = clamp(buf.rotY, rotYMin.value, rotYMax.value)
      isYChecked.value = buf.isYChecked

    if (typeof buf.rotZ === 'number')
      rotZ.value = clamp(buf.rotZ, rotZMin.value, rotZMax.value)
      isZChecked.value = buf.isZChecked
  }

  let pollingInterval: ReturnType<typeof setInterval> | null = null

  // timer (inchangé)…
  const TIMER_DURATION = 60
  const timerSeconds = ref(TIMER_DURATION)
  let timerInterval: number
  function startTimer() {
    clearInterval(timerInterval)
    timerSeconds.value = TIMER_DURATION
    timerInterval = window.setInterval(() => {
      timerSeconds.value = Math.max(timerSeconds.value - 1, 0)
      if (timerSeconds.value === 0) clearInterval(timerInterval)
    }, 1000)
  }
  // fonctions couleur…
  function hexToRgb(hex: string) {
    const h = hex.replace('#', '')
    const bi = parseInt(h, 16)
    return { r: (bi >> 16) & 0xff, g: (bi >> 8) & 0xff, b: bi & 0xff }
  }
  function rgbToHex(r: number, g: number, b: number) {
    const to2 = (x: number) => x.toString(16).padStart(2, '0')
    return `#${to2(r)}${to2(g)}${to2(b)}`
  }
  function lerp(a: number, b: number, t: number) { return a + (b - a) * t }

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
        const a = hexToRgb(c0), b = hexToRgb(c1)
        return rgbToHex(
          Math.round(lerp(a.r, b.r, t)),
          Math.round(lerp(a.g, b.g, t)),
          Math.round(lerp(a.b, b.b, t))
        )
      }
    }
    return colorStops.at(-1)!.color
  })

  const timerText = computed(() => {
    const m = Math.floor(timerSeconds.value / 60)
    const s = timerSeconds.value % 60
    return `${m}:${String(s).padStart(2, '0')}`
  })

  onMounted(async () => {
    // 1) charge bornes
    await loadConfig()
    // 2) démarre timer
    startTimer()
    // 3) WS push
    artClient.onMessage((msg: any) => {
      if (msg.action === 'get_buffer' && msg.buffer) applyBuffer(msg.buffer)
    })
    // 4) initial + polling HTTP
    try { applyBuffer(await artClient.getBuffer()) } catch {}
    pollingInterval = setInterval(async () => {
      try { applyBuffer(await artClient.getBuffer()) } catch {}
    }, 50)

    // 5) Three.js (inchangé)
    const canvas = canvasRef.value
    if (canvas) {
      const scene = new THREE.Scene()
      const camera = new THREE.PerspectiveCamera(60, canvas.clientWidth / canvas.clientHeight, 0.1, 1000)
      camera.position.set(0, -0.30, 2)
      const renderer = new THREE.WebGLRenderer({ antialias: true, canvas })
      renderer.setSize(canvas.clientWidth, canvas.clientHeight)
      scene.add(new THREE.AmbientLight(0xffffff, 1))
      const spot = new THREE.SpotLight(0xffffff, 450)
      spot.angle = Math.PI / 3; spot.position.set(0, 0, 5)
      scene.add(spot)
      let obj: THREE.Object3D | null = null
      new MTLLoader().setPath('/models/module2/').load('Enter a title.mtl', mats => {
        mats.preload()
        new OBJLoader().setMaterials(mats).setPath('/models/module2/').load('Enter a title.obj', o => {
          const c = new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3())
          const grp = new THREE.Group()
          o.position.sub(c); grp.add(o); scene.add(grp); obj = grp
        })
      })
      ;(function animate() {
        requestAnimationFrame(animate)
        if (obj) {
          obj.rotation.x = rotX.value
          obj.rotation.y = rotY.value
          obj.rotation.z = rotZ.value
        }
        renderer.render(scene, camera)
      })()
    }
  })

  onBeforeUnmount(() => {
    if (pollingInterval) clearInterval(pollingInterval)
    clearInterval(timerInterval)
  })

  return {
    rotX, rotY, rotZ,
    rotXMin, rotXMax,
    rotYMin, rotYMax,
    rotZMin, rotZMax,
    timerColor, timerText,
    isXChecked, isYChecked, isZChecked
  }
}
