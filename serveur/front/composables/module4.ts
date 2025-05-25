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
  // ❌ Pas de dessin côté serveur
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
  for (const [path, url] of Object.entries(imgModules)) {
    const name = path.split('/').pop()!.replace('.png', '')
    const img = new Image()
    img.src = url
    objectImages[name] = img
  }

  // 2️⃣ Couleurs par canal et stockage des canevas
  const colorMap: Record<string, [number, number, number]> = {
    '1': [255, 0, 0],   // canal 1 → rouge
    '2': [0, 255, 0],   // canal 2 → vert
    '3': [0, 0, 255],   // canal 3 → bleu
  }
  const brushCanvases: Record<string, HTMLCanvasElement[]> = {
    '1': [], '2': [], '3': []
  }
  // Charge toutes les images de brushes (grayscale)
  const brushModules = import.meta.glob<string>(
    '~/assets/modules/4/images/brushes/*.png',
    { eager: true, as: 'url' }
  )

  // 3️⃣ Stockage local
  const strokes = ref<Stroke[]>([])
  const objects = ref<ArtObject[]>([])

  // 4️⃣ Fonctions de dessin
  const scale = 3
  function drawStroke(ctx: CanvasRenderingContext2D, s: Stroke) {
    const canvases = brushCanvases[s.tool_id] || []
    if (canvases.length === 0) return
    const bc = canvases[0] // un seul brush par canal
    const px = s.x * scale
    const py = s.y * scale
    const size = (s.size || 5) * scale
    const ang = s.angle || 0

    ctx.save()
    ctx.translate(px, py)
    ctx.rotate(ang)
    ctx.drawImage(bc, -size / 2, -size / 2, size, size)
    ctx.restore()
  }

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

  function drawBuffer(buf: {
    newStrokes?: Stroke[]
    removeStrokes?: string[]
    newObjects?: ArtObject[]
    removeObjects?: string[]
  }) {
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
    if (buf.removeStrokes) {
      strokes.value = strokes.value.filter(s => !buf.removeStrokes!.includes(s.id))
    }
    if (buf.newObjects) {
      objects.value.push(...buf.newObjects)
    }
    if (buf.removeObjects) {
      objects.value = objects.value.filter(o => !buf.removeObjects!.includes(o.id))
    }

    const canvas = canvasRef.value
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    strokes.value.forEach(s => drawStroke(ctx, s))
    objects.value.forEach(o => drawObject(ctx, o))
  }

  // 5️⃣ Intégration Artineo WS et préparation des brushes
  let intervalId: ReturnType<typeof setInterval> | null = null

  onMounted(() => {
    console.log('Module 4: Kinect')

    // Assigner brush1→canal1, brush2→canal2, brush3→canal3
    const mapping: Record<string, string> = {
      '1': 'brush1.png',
      '2': 'brush2.png',
      '3': 'brush3.png'
    }

    for (const [toolId, fileName] of Object.entries(mapping)) {
      // Trouve l'URL correspondant au fichier
      const entry = Object.entries(brushModules).find(([path]) =>
        path.endsWith(fileName)
      )
      if (!entry) {
        console.warn(`Brush ${fileName} introuvable pour le canal ${toolId}`)
        continue
      }
      const url = entry[1]
      const img = new Image()
      img.src = url
      img.onload = () => {
        const cw = img.width, ch = img.height
        const c = document.createElement('canvas')
        c.width = cw; c.height = ch
        const ctx = c.getContext('2d')!
        ctx.drawImage(img, 0, 0)
        const idata = ctx.getImageData(0, 0, cw, ch)
        const d = idata.data
        const [r, g, b] = colorMap[toolId]
        for (let i = 0; i < d.length; i += 4) {
          const lum = d[i]       // niveau de gris
          d[i] = r           // teinte rouge/vert/bleu
          d[i + 1] = g
          d[i + 2] = b
          d[i + 3] = lum         // alpha = intensité initiale
        }
        ctx.putImageData(idata, 0, 0)
        brushCanvases[toolId].push(c)
      }
    }

    // Écoute WS pour recevoir le buffer
    artClient.onMessage(msg => {
      if (msg.action === 'get_buffer' && msg.buffer) {
        drawBuffer(msg.buffer)
      }
    })

    // Récupération initiale et polling HTTP
    artClient.getBuffer()
      .then(buf => drawBuffer(buf))
      .catch(() => {/* ignore */ })

    intervalId = setInterval(() => {
      artClient.getBuffer()
        .then(buf => drawBuffer(buf))
        .catch(() => {/* ignore */ })
    }, 100)
  })

  onBeforeUnmount(() => {
    if (intervalId !== null) clearInterval(intervalId)
    artClient.close()
  })

  return { strokes, objects }
}
