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

export default function use4kinect(canvasRef: Ref<HTMLCanvasElement | null>) {
  // ↪ Guard SSR : on ne veut pas exécuter tout le code graphiques en server-side
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
    const name = path.split('/').pop()!.replace('.png', '')
    const img = new Image()
    img.src = url
    objectImages[name] = img
  }

  // 2️⃣ Brushes niveaux de gris
  const brushCanvases: Record<string, HTMLCanvasElement[]> = {
    '1': [], '2': [], '3': []
  }
  const colorMap: Record<string, [number, number, number]> = {
    '1': [255, 0, 0],
    '2': [0, 255, 0],
    '3': [0, 0, 255]
  }
  const brushModules = import.meta.glob<string>(
    '~/assets/modules/4/images/brushes/*.png',
    { eager: true, as: 'url' }
  )
  const rawBrushImages: HTMLImageElement[] = []
  for (const url of Object.values(brushModules)) {
    const img = new Image()
    img.src = url
    rawBrushImages.push(img)
  }

  function prepareBrushes() {
    rawBrushImages.forEach(img => {
      const cw = img.width, ch = img.height
      for (const [toolId, [r, g, b]] of Object.entries(colorMap)) {
        const c = document.createElement('canvas')
        c.width = cw; c.height = ch
        const ctx = c.getContext('2d')!
        ctx.drawImage(img, 0, 0)
        const idata = ctx.getImageData(0, 0, cw, ch)
        const d = idata.data
        for (let i = 0; i < d.length; i += 4) {
          const lum = d[i]
          d[i]     = r
          d[i + 1] = g
          d[i + 2] = b
          d[i + 3] = lum
        }
        ctx.putImageData(idata, 0, 0)
        brushCanvases[toolId].push(c)
      }
    })
    console.log('✅ Brushes prêts:',
      Object.entries(brushCanvases)
        .map(([t, arr]) => `${t}→${arr.length}`)
        .join(', ')
    )
  }

  // 3️⃣ Stockage local
  const strokes = ref<Stroke[]>([])
  const objects = ref<ArtObject[]>([])

  // 4️⃣ Dessin
  const scale = 3
  function drawStroke(ctx: CanvasRenderingContext2D, s: Stroke) {
    const canvases = brushCanvases[s.tool_id] || []
    if (!canvases.length) return
    const bc = canvases[Math.floor(Math.random() * canvases.length)]
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

  // 5️⃣ Traitement du buffer reçu
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

  // 6️⃣ Intégration Artineo WS
  let intervalId: ReturnType<typeof setInterval> | null = null

  onMounted(() => {
    console.log('Module 4: Kinect')
    // Préparer les brushes une fois les images chargées
    Promise.all(
      rawBrushImages.map(img => {
        console.log('Préchargement brush', img.src)
        return img.complete
          ? Promise.resolve()
          : new Promise<void>(res => {
              img.onload = () => {
                console.log('Image chargée', img.src)
                res()
              }
            })
      })
    ).then(() => {
      console.log('✅ Tous les brushes chargés, préparation…')
      prepareBrushes()
    })

    artClient.onMessage(msg => {
      if (msg.action === 'get_buffer' && msg.buffer) {
        drawBuffer(msg.buffer)
      }
    })

    artClient.getBuffer()
      .then(buf => drawBuffer(buf))
      .catch(() => {})

    intervalId = setInterval(() => {
      artClient.getBuffer()
        .then(buf => drawBuffer(buf))
        .catch(() => {})
    }, 100)
  })

  onBeforeUnmount(() => {
    if (intervalId !== null) clearInterval(intervalId)
    // Ne pas fermer artClient : connexion partagée
  })

  return { strokes, objects }
}
