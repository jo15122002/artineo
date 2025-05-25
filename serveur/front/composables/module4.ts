// front/composables/module4.ts
import type { Ref } from 'vue'
import { ref, onMounted, onBeforeUnmount } from 'vue'
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

export default function use4kinect(canvasRef: Ref<HTMLCanvasElement | null>) {
  // SSR guard: nothing to do on server
  if (!process.client) {
    const stub: any = ref(null)
    return {
      strokes: stub as Ref<Stroke[]>,
      objects: stub as Ref<ArtObject[]>
    }
  }

  const moduleId = 4
  const artClient = useArtineo(moduleId)

  // 1️⃣ Préchargement des sprites d'objets
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

  // 2️⃣ Préchargement d’un brush fixe par canal (brush1.png, brush2.png, brush3.png)
  const brushImages: Record<string, HTMLImageElement> = {}
  const brushModules = import.meta.glob<string>(
    '~/assets/modules/4/images/brushes/brush?.png',
    { eager: true, as: 'url' }
  )
  for (const path in brushModules) {
    const url = brushModules[path]
    const file = path.split('/').pop()!
    const match = file.match(/^brush([1-6])\.png$/)
    if (match) {
      const toolId = match[1]
      const img = new Image()
      img.src = url
      brushImages[toolId] = img
    }
  }

  // 3️⃣ Mapping des couleurs d’overlay par bouton
  const buttonColors: Record<number, string> = {
    1: 'rgba(255, 0,   0,   0.3)',
    2: 'rgba(0,   255, 0,   0.3)',
    3: 'rgba(0,   0,   255, 0.3)',
    4: 'rgba(255, 255, 0,   0.3)',
    5: 'rgba(255, 0,   255, 0.3)',
    6: 'rgba(0,   255, 255, 0.3)',
  }
  let currentButton = 1 // par défaut

  // 4️⃣ Stockage local des strokes et objets
  const strokes = ref<Stroke[]>([])
  const objects = ref<ArtObject[]>([])

  // 5️⃣ Fonction de rendu des strokes
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

  // 6️⃣ Fonction de rendu des objets
  function drawObject(ctx: CanvasRenderingContext2D, o: ArtObject) {
    const img = objectImages[o.shape]
    if (img && img.complete) {
      const w = o.w * scale
      const h = o.h * scale
      const x = o.cx * scale - w / 2
      const y = o.cy * scale - h / 2
      ctx.drawImage(img, x, y, w, h)
    } else {
      ctx.fillStyle = '#000'
      ctx.fillRect(o.cx * scale - 5, o.cy * scale - 5, 10, 10)
    }
  }

  // 7️⃣ Traitement et rendu complet du buffer
  function drawBuffer(buf: {
    newStrokes?: Stroke[]
    removeStrokes?: string[]
    newObjects?: ArtObject[]
    removeObjects?: string[]
    button?: number
  }) {
    // 7.1) Gestion du bouton
    if (typeof buf.button === 'number') {
      currentButton = buf.button
    }

    // 7.2) Ajout des nouveaux traits
    if (buf.newStrokes) {
      buf.newStrokes.forEach(s => {
        if (!strokes.value.some(old => old.id === s.id)) {
          if (s.angle === undefined) {
            s.angle = Math.random() * Math.PI * 2
          }
          strokes.value.push(s)
        }
      })
    }
    // 7.3) Suppression des traits effacés
    if (buf.removeStrokes) {
      strokes.value = strokes.value.filter(s => !buf.removeStrokes!.includes(s.id))
    }
    // 7.4) Objets
    if (buf.newObjects) {
      objects.value.push(...buf.newObjects)
    }
    if (buf.removeObjects) {
      objects.value = objects.value.filter(o => !buf.removeObjects!.includes(o.id))
    }

    // 7.5) Rendu sur le canvas
    const canvas = canvasRef.value
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    // fond blanc
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    // strokes et objets
    strokes.value.forEach(s => drawStroke(ctx, s))
    objects.value.forEach(o => drawObject(ctx, o))
    // overlay rectangle de couleur
    const overlay = buttonColors[currentButton] || buttonColors[1]
    ctx.fillStyle = overlay
    ctx.fillRect(0, 0, canvas.width, canvas.height)
  }

  // 8️⃣ Intégration Artineo WS + polling HTTP fallback
  let intervalId: ReturnType<typeof setInterval> | null = null

  onMounted(() => {
    // 8.1) via WebSocket
    artClient.onMessage(msg => {
      if (msg.action === 'get_buffer' && msg.buffer) {
        drawBuffer(msg.buffer)
      }
    })
    // 8.2) HTTP fallback initial + intervalle
    artClient.getBuffer()
      .then(buf => drawBuffer(buf))
      .catch(() => { })
    intervalId = setInterval(() => {
      artClient.getBuffer()
        .then(buf => drawBuffer(buf))
        .catch(() => { })
    }, 100)
  })

  onBeforeUnmount(() => {
    // if (intervalId !== null) clearInterval(intervalId)
    artClient.close()
  })

  return { strokes, objects }
}
