// File: serveur/front/composables/module4.ts
import type { Ref } from 'vue'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useArtineo } from './useArtineo'

export interface Stroke {
  id: string
  tool_id: string
  x: number
  y: number
  size: number
  angle?: number
}

export interface ArtObject {
  id: string
  shape: string
  cx: number
  cy: number
  w: number
  h: number
  angle: number
  scale: number
}

/**
 * Composable for module 4 (Kinect + button overlay), plus timer controls.
 */
export default function useModule4(
  canvasRef: Ref<HTMLCanvasElement | null>,
  stepRef: Ref<number>
) {
  // SSR guard
  if (!process.client) {
    const stubAny = ref<any>(null)
    const stubNum = ref(60)
    const stubText = ref('1:00')
    const stubColor = ref('#2626FF')
    const noop = () => { }
    return {
      strokes: stubAny as Ref<Stroke[]>,
      objects: stubAny as Ref<ArtObject[]>,
      backgrounds: stubAny as Ref<ArtObject[]>,
      timerSeconds: stubNum,
      timerText: stubText,
      timerColor: stubColor,
      startTimer: noop,
      pauseTimer: noop,
      resumeTimer: noop,
      resetTimer: noop
    }
  }

  // Module IDs
  const kinectModuleId = 4
  const buttonModuleId = 41

  // Artineo clients
  const artClientKinect = useArtineo(kinectModuleId)
  const artClientButton = useArtineo(buttonModuleId)

  // 1️⃣ Load assets via Vite glob
  const objectImages: Record<string, HTMLImageElement> = {}
  const imgModules = import.meta.glob<string>(
    '~/assets/modules/4/images/objects/*.png',
    { eager: true, as: 'url' }
  )
  for (const path in imgModules) {
    const url = imgModules[path]
    const name = path.split('/').pop()!.replace(/\.png$/, '')
    const img = new Image()
    img.src = url
    objectImages[name] = img
  }

  const brushImages: Record<string, HTMLImageElement> = {}
  const brushModules = import.meta.glob<string>(
    '~/assets/modules/4/images/brushes/brush?.png',
    { eager: true, as: 'url' }
  )
  for (const path in brushModules) {
    const m = path.match(/brush([1-6])\.png$/)
    if (m) {
      const img = new Image()
      img.src = brushModules[path]
      brushImages[m[1]] = img
    }
  }

  const maskModules = import.meta.glob<string>(
    '~/assets/modules/4/images/masks/mask.png',
    { eager: true, as: 'url' }
  )
  const maskPath = Object.values(maskModules)[0]!
  const maskImage = new Image()
  maskImage.src = maskPath

  // Offscreen canvas for mask compositing
  const maskCanvas = document.createElement('canvas')
  let maskCtx: CanvasRenderingContext2D | null = null

  // 2️⃣ Local state
  const strokes = ref<Stroke[]>([])
  const objects = ref<ArtObject[]>([])
  const backgrounds = ref<ArtObject[]>([])
  const scale = 3
  let currentButton = 1

  // 3️⃣ Timer logic
  const TIMER_DURATION = 60
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

  function pauseTimer() {
    if (timerInterval) {
      clearInterval(timerInterval)
      timerInterval = undefined
    }
  }

  function resumeTimer() {
    if (!timerInterval && timerSeconds.value > 0) {
      timerInterval = window.setInterval(() => {
        timerSeconds.value = Math.max(timerSeconds.value - 1, 0)
        if (timerSeconds.value === 0 && timerInterval) {
          clearInterval(timerInterval)
        }
      }, 1000)
    }
  }

  function resetTimer() {
    pauseTimer()
    timerSeconds.value = TIMER_DURATION
  }

  // Timer color gradient
  function hexToRgb(hex: string) {
    const h = hex.replace('#', '')
    const bigint = parseInt(h, 16)
    return {
      r: (bigint >> 16) & 0xff,
      g: (bigint >> 8) & 0xff,
      b: bigint & 0xff
    }
  }
  function rgbToHex(r: number, g: number, b: number) {
    const to2 = (x: number) => x.toString(16).padStart(2, '0')
    return `#${to2(r)}${to2(g)}${to2(b)}`
  }
  function lerp(a: number, b: number, t: number) { return a + (b - a) * t }

  const colorStops = [
    { p: 1.0, color: '#2626FF' },
    { p: 0.6, color: '#FA81C3' },
    { p: 0.3, color: '#FA4923' }
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
    return colorStops[colorStops.length - 1].color
  })

  const timerText = computed(() => {
    const m = Math.floor(timerSeconds.value / 60)
    const s = timerSeconds.value % 60
    return `${m}:${String(s).padStart(2, '0')}`
  })

  let currentLengthStrokes = 0
  let normalStrokes = 0

  // 4️⃣ Draw buffer (strokes, backgrounds, objects, overlay)
  function drawBuffer(buf: {
    newStrokes?: Stroke[]
    removeStrokes?: string[]
    newBackgrounds?: ArtObject[]
    removeBackgrounds?: string[]
    newObjects?: ArtObject[]
    removeObjects?: string[]
    button?: number
    timerControl?: 'reset' | 'pause' | 'resume'
  }) {
    // handle timerControl
    if (buf.timerControl === 'pause') pauseTimer()
    if (buf.timerControl === 'resume') resumeTimer()
    if (buf.timerControl === 'reset') resetTimer()

    // button overlay event
    if (typeof buf.button === 'number') {
      currentButton = buf.button
    }

    // update strokes
    if (buf.newStrokes) {
      // buf.newStrokes.forEach(s => {
      //   if (!strokes.value.some(x=>x.id===s.id)) {
      //     s.angle ??= Math.random()*Math.PI*2
      //     strokes.value.push(s)
      //   }
      // })
      const newStrokes = buf.newStrokes.filter(s => !strokes.value.some(x => x.id === s.id))
      normalStrokes += newStrokes.length
      for (let newStroke of newStrokes) {
        newStroke.angle ??= Math.random() * Math.PI * 2
        strokes.value.push(newStroke)
      }
    }
    if (buf.removeStrokes) {
      normalStrokes -= buf.removeStrokes.length
      strokes.value = strokes.value.filter(s => !buf.removeStrokes!.includes(s.id))
    }

    // update backgrounds
    if (buf.newBackgrounds) {
      buf.newBackgrounds.forEach(b => {
        if (!backgrounds.value.some(x => x.id === b.id)) backgrounds.value.push(b)
      })
    }
    if (buf.removeBackgrounds) {
      backgrounds.value = backgrounds.value.filter(b => !buf.removeBackgrounds!.includes(b.id))
    }

    // update objects
    if (buf.newObjects) {
      buf.newObjects.forEach(o => {
        if (!objects.value.find(x => x.id === o.id)) objects.value.push(o)
      })
    }
    if (buf.removeObjects) {
      objects.value = objects.value.filter(o => !buf.removeObjects!.includes(o.id))
    }

    // prepare canvases
    const canvas = canvasRef.value!
    const ctx = canvas.getContext('2d')!
    if (!maskCtx
      || maskCanvas.width !== canvas.width
      || maskCanvas.height !== canvas.height
    ) {
      maskCanvas.width = canvas.width
      maskCanvas.height = canvas.height
      maskCtx = maskCanvas.getContext('2d')
    }

    // clear main canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    // mask strokes
    if (maskCtx && maskImage.complete && strokes.value.length > 0) {
      maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height)
      maskCtx.globalCompositeOperation = 'source-over'
      if (currentLengthStrokes !== strokes.value.length) {
        console.log(`Normal strokes: ${normalStrokes}, Current strokes: ${strokes.value.length}`)
        console.log(`Liste des strokes:`, strokes.value);
      }
      currentLengthStrokes = strokes.value.length
      strokes.value.forEach(s => {
        const img = brushImages[1]
        if (!img?.complete) return
        const px = s.x * scale, py = s.y * scale
        const sz = Math.min(Math.max((s.size ?? 5) * scale * 1.5, 45), 90)
        const ang = s.angle ?? 0

        maskCtx!.save()
        maskCtx!.translate(px, py)
        maskCtx!.rotate(ang)
        maskCtx!.drawImage(img, -sz / 2, -sz / 2, sz, sz)
        maskCtx!.restore()
      })
      maskCtx.globalCompositeOperation = 'source-in'
      maskCtx.drawImage(maskImage, 0, 0, maskCanvas.width, maskCanvas.height)
      maskCtx.globalCompositeOperation = 'source-over'
      ctx.drawImage(maskCanvas, 0, 0)
    }

    // draw backgrounds
    backgrounds.value.forEach(b => {
      const img = objectImages[b.shape]
      if (img?.complete) {
        const cw = canvas.width, aspect = img.naturalHeight / img.naturalWidth
        const w = cw, h = cw * aspect, x0 = 0, y0 = canvas.height - h
        ctx.drawImage(img, x0, y0, w, h)
      }
    })

    // draw objects
    objects.value.forEach(o => {
      const img = objectImages[o.shape]
      if (img?.complete) {
        const w = o.w * scale, h = o.h * scale
        const x0 = o.cx * scale - w / 2, y0 = o.cy * scale - h / 2
        ctx.drawImage(img, x0, y0, w, h)
      }
    })

    // overlay
    ctx.fillStyle = {
      1: 'rgba(83,160,236,0.2)',
      2: 'rgba(252,191,0,0.2)',
      3: 'rgba(147,146,183,0.6)'
    }[currentButton] || 'rgba(83,160,236,0.2)'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
  }

  // polling fallbacks
  let pollKinect: ReturnType<typeof setInterval> | null = null
  let pollButton: ReturnType<typeof setInterval> | null = null

  onMounted(() => {
    // start timer on mount
    // startTimer()

    // subscribe Kinect WS
    artClientKinect.onMessage((msg: any) => {
      if (msg.action === 'get_buffer' && msg.buffer) drawBuffer(msg.buffer)
    })
    artClientKinect.getBuffer().then(drawBuffer).catch(() => { })
    pollKinect = setInterval(() => {
      artClientKinect.getBuffer().then(drawBuffer).catch(() => { })
    }, 100)

    // subscribe Button WS
    artClientButton.onMessage((msg: any) => {
      if (msg.action === 'get_buffer' && msg.buffer) drawBuffer(msg.buffer)
    })
    artClientButton.getBuffer().then(drawBuffer).catch(() => { })
    pollButton = setInterval(() => {
      artClientButton.getBuffer().then(drawBuffer).catch(() => { })
    }, 100)

    // keyboard for sandbox
    window.addEventListener('keydown', onKeydown)
  })

  onBeforeUnmount(() => {
    if (pollKinect) clearInterval(pollKinect)
    if (pollButton) clearInterval(pollButton)
    pauseTimer()
    window.removeEventListener('keydown', onKeydown)
    artClientKinect.close()
    artClientButton.close()
  })

  // key bindings
  function onKeydown(ev: KeyboardEvent) {
    const binding: any = {
      // a few examples...
      a: { shape: 'landscape_fields', cx: 50, cy: 80 },
      1: { button: 1 }, 2: { button: 2 }, 3: { button: 3 }
    }[ev.key]
    if (!binding) return
    ev.preventDefault()
    if (binding.button) {
      currentButton = binding.button
      drawBuffer({ button: currentButton })
    } else if (binding.shape) {
      // simplified addImage logic...
      const o: ArtObject = {
        id: Date.now().toString(),
        shape: binding.shape,
        cx: binding.cx, cy: binding.cy,
        w: binding.w || 50 / scale, h: binding.h || 50 / scale,
        angle: 0, scale: 1
      }
      objects.value.push(o)
      drawBuffer({})
    }
  }

  return {
    strokes,
    objects,
    backgrounds,
    timerSeconds,
    timerText,
    timerColor,
    startTimer,
    pauseTimer,
    resumeTimer,
    resetTimer
  }
}
