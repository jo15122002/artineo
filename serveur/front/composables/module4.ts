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
 * Composable for tool 4 (Kinect + button overlay).
 * Renders strokes, objects, backgrounds, and a color overlay
 * according to a "button" value received over WS.
 */
export default function use4kinect(canvasRef: Ref<HTMLCanvasElement | null>) {
  // SSR guard: no DOM on server
  if (!process.client) {
    const stub: any = ref(null)
    return {
      strokes: stub as Ref<Stroke[]>,
      objects: stub as Ref<ArtObject[]>,
      backgrounds: stub as Ref<ArtObject[]>
    }
  }

  // two module IDs: one for kinect data, one for button events
  const kinectModuleId = 4
  const buttonModuleId = 41

  const artClientKinect = useArtineo(kinectModuleId)
  const artClientButton = useArtineo(buttonModuleId)

  // 1️⃣ load object sprites
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

  // 2️⃣ load a fixed brush image per tool (brush1.png, brush2.png, brush3.png)
  const brushImages: Record<string, HTMLImageElement> = {}
  const brushModules = import.meta.glob<string>(
    '~/assets/modules/4/images/brushes/brush?.png',
    { eager: true, as: 'url' }
  )
  for (const path in brushModules) {
    const url = brushModules[path]
    const file = path.split('/').pop()!
    const m = file.match(/^brush([1-6])\.png$/)
    if (m) {
      const toolId = m[1]
      const img = new Image()
      img.src = url
      brushImages[toolId] = img
    }
  }

  // 3️⃣ map button IDs to RGBA overlays
  const buttonColors: Record<number, string> = {
    1: 'rgba(83, 160, 236, 0.2)',
    2: 'rgba(0, 255, 0, 0.3)',
    3: 'rgba(0, 0, 255, 0.3)',
    4: 'rgba(255, 255, 0, 0.3)',
    5: 'rgba(255, 0, 255, 0.3)',
    6: 'rgba(0, 255, 255, 0.3)',
  }
  let currentButton = 1  // default

  // 4️⃣ local state
  const strokes = ref<Stroke[]>([])
  const objects = ref<ArtObject[]>([])
  const backgrounds = ref<ArtObject[]>([])

  // 5️⃣ draw a stroke using its fixed brush
  const scale = 3
  function drawStroke(ctx: CanvasRenderingContext2D, s: Stroke) {
    const img = brushImages[s.tool_id]
    if (!img || !img.complete) return
    const px = s.x * scale
    const py = s.y * scale
    const size = (s.size ?? 5) * scale
    const ang = s.angle ?? 0

    ctx.save()
    ctx.translate(px, py)
    ctx.rotate(ang)
    ctx.drawImage(img, -size / 2, -size / 2, size, size)
    ctx.restore()
  }

  // 6️⃣ draw an object sprite (non-background)
  function drawObject(ctx: CanvasRenderingContext2D, o: ArtObject) {
    const img = objectImages[o.shape]
    if (img && img.complete) {
      const w = o.w * scale, h = o.h * scale
      const x = o.cx * scale - w / 2, y = o.cy * scale - h / 2
      ctx.drawImage(img, x, y, w, h)
    } else {
      // fallback: small dot
      ctx.fillStyle = '#000'
      ctx.fillRect(o.cx * scale - 2, o.cy * scale - 2, 4, 4)
    }
  }

  // 6️⃣bis draw a background sprite full-width, aligned en bas
  function drawBackground(ctx: CanvasRenderingContext2D, b: ArtObject) {
    const img = objectImages[b.shape]
    if (!img || !img.complete) return

    // La largeur du canvas
    const canvasWidth = ctx.canvas.width
    // Calculer la hauteur en conservant l'aspect ratio
    const aspect = img.naturalHeight / img.naturalWidth
    const drawWidth = canvasWidth
    const drawHeight = canvasWidth * aspect

    // Positionner pour que le bas de l'image touche le bas du canvas
    const x = 0
    const y = ctx.canvas.height - drawHeight

    ctx.drawImage(img, x, y, drawWidth, drawHeight)
  }

  // 7️⃣ handle incoming diff buffer
  function drawBuffer(buf: {
    newStrokes?: Stroke[]
    removeStrokes?: string[]
    newBackgrounds?: ArtObject[]
    removeBackgrounds?: string[]
    newObjects?: ArtObject[]
    removeObjects?: string[]
    button?: number
  }) {
    if (!buf) return

    // 7.1) button event
    if (typeof buf.button === 'number') {
      currentButton = buf.button
    }

    // 7.2) add strokes
    if (buf.newStrokes) {
      buf.newStrokes.forEach(s => {
        if (!strokes.value.some(x => x.id === s.id)) {
          if (s.angle === undefined) {
            s.angle = Math.random() * Math.PI * 2
          }
          strokes.value.push(s)
        }
      })
    }
    // 7.3) remove strokes
    if (buf.removeStrokes) {
      strokes.value = strokes.value.filter(s => !buf.removeStrokes!.includes(s.id))
    }

    // 7.4) backgrounds
    if (buf.newBackgrounds) {
      // remplace les backgrounds existants avec ceux reçus
      backgrounds.value = backgrounds.value.concat(
        buf.newBackgrounds.filter(nb => !backgrounds.value.some(b => b.id === nb.id))
      )
    }
    if (buf.removeBackgrounds) {
      backgrounds.value = backgrounds.value.filter(b => !buf.removeBackgrounds!.includes(b.id))
    }

    // 7.5) objects
    if (buf.newObjects) {
      buf.newObjects.forEach(o => {
        if (!objects.value.find(prev => prev.id === o.id)) {
          objects.value.push(o)
        }
      })
    }
    if (buf.removeObjects) {
      objects.value = objects.value.filter(o => !buf.removeObjects!.includes(o.id))
    }

    // 7.6) render everything
    const canvas = canvasRef.value
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    // clear
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    // optional background fill
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    // 7.6.1) draw backgrounds **plein écran**, aligné en bas
    backgrounds.value.forEach(b => drawBackground(ctx, b))

    // 7.6.2) draw strokes & objects
    strokes.value.forEach(s => drawStroke(ctx, s))
    objects.value.forEach(o => drawObject(ctx, o))

    // 7.6.3) finally overlay color rectangle
    const overlay = buttonColors[currentButton] || buttonColors[1]
    ctx.fillStyle = overlay
    ctx.fillRect(0, 0, canvas.width, canvas.height)
  }

  // 8️⃣ WebSocket + HTTP fallback polling
  let pollingIntervalKinect: ReturnType<typeof setInterval> | null = null
  let pollingIntervalButton: ReturnType<typeof setInterval> | null = null
  let isKinectSubscribed = false
  let isButtonSubscribed = false

  onMounted(async () => {
    console.log('Module 4: Kinect + Button')
    // subscribe to Kinect updates
    if (!isKinectSubscribed) {
      isKinectSubscribed = true
      artClientKinect.onMessage(msg => {
        if (msg.action === 'get_buffer' && msg.buffer) {
          drawBuffer(msg.buffer)
        }
      })

      artClientKinect.getBuffer()
        .then(buf => drawBuffer(buf))
        .catch(e => console.error('[Artineo][Kinect] init error', e))

      pollingIntervalKinect = setInterval(() => {
        artClientKinect.getBuffer()
          .then(buf => drawBuffer(buf))
          .catch(() => {})
      }, 100)
    }

    // subscribe to Button updates
    if (!isButtonSubscribed) {
      isButtonSubscribed = true
      artClientButton.onMessage(msg => {
        if (msg.action === 'get_buffer' && msg.buffer) {
          drawBuffer(msg.buffer)
        }
      })

      artClientButton.getBuffer()
        .then(buf => drawBuffer(buf))
        .catch(e => console.error('[Artineo][Button] init error', e))

      pollingIntervalButton = setInterval(() => {
        artClientButton.getBuffer()
          .then(buf => drawBuffer(buf))
          .catch(() => {})
      }, 100)
    }
  })

  onBeforeUnmount(() => {
    if (pollingIntervalKinect) {
      clearInterval(pollingIntervalKinect)
      pollingIntervalKinect = null
    }
    if (pollingIntervalButton) {
      clearInterval(pollingIntervalButton)
      pollingIntervalButton = null
    }
    artClientKinect.close()
    isKinectSubscribed = false

    artClientButton.close()
    isButtonSubscribed = false
  })

  return { strokes, objects, backgrounds }
}
