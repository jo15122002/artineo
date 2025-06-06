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
  // En SSR, on renvoie des stubs
  if (!process.client) {
    const stubStrokes: Ref<Stroke[]> = ref([])
    const stubObjects: Ref<ArtObject[]> = ref([])
    return { strokes: stubStrokes, objects: stubObjects }
  }

  // Création (et cache) d’un client Artineo unique pour module = 4
  const artClient = useArtineo(4)

  // Préchargement des sprites d’objets
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

  // Chargement des brushes niveaux de gris
  const brushCanvases: Record<string, HTMLCanvasElement[]> = { '1': [], '2': [], '3': [] }
  const colorMap: Record<string, [number, number, number]> = {
    '1': [255, 0, 0],
    '2': [0, 255, 0],
    '3': [0, 0, 255],
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

  // Référentiels pour dessiner
  const strokes = ref<Stroke[]>([])
  const objects = ref<ArtObject[]>([])

  // Fonctions de dessin
  const scale = 3
  function drawStroke(ctx: CanvasRenderingContext2D, s: Stroke) {
    const canvases = brushCanvases[s.tool_id] || []
    if (!canvases.length) return
    const bc = canvases[Math.floor(Math.random() * canvases.length)]
    const px = s.x * scale
    const py = s.y * scale
    const size = (s.size || 5) * scale
    const ang = s.angle ?? 0
    ctx.save()
    ctx.translate(px, py)
    ctx.rotate(ang)
    ctx.drawImage(bc, -size / 2, -size / 2, size, size)
    ctx.restore()
  }

  function drawObject(ctx: CanvasRenderingContext2D, o: ArtObject) {
    const img = objectImages[o.shape]
    if (img && img.complete) {
      const w = o.w * scale, h = o.h * scale
      const x = o.cx * scale - w / 2, y = o.cy * scale - h / 2
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
        if (!strokes.value.find(prev => prev.id === s.id)) {
          s.angle = s.angle ?? Math.random() * Math.PI * 2
          strokes.value.push(s)
        }
      })
    }
    if (buf.removeStrokes) {
      strokes.value = strokes.value.filter(s => !buf.removeStrokes!.includes(s.id))
    }
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

    const canvas = canvasRef.value
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    strokes.value.forEach(s => drawStroke(ctx, s))
    objects.value.forEach(o => drawObject(ctx, o))
  }

  let pollingInterval: ReturnType<typeof setInterval> | null = null
  let isSubscribed = false

  onMounted(() => {
    console.log('Module 4: Kinect')

    // Préparer les brushes
    Promise.all(
      rawBrushImages.map(img => 
        img.complete ? Promise.resolve() : new Promise<void>(res => { img.onload = () => res() })
      )
    ).then(() => {
      console.log('✅ Tous les brushes chargés')
      prepareBrushes()
    })

    // 1) Abonnement WS unique
    if (!isSubscribed) {
      isSubscribed = true
      artClient.onMessage((msg: any) => {
        if (msg.action === 'get_buffer' && msg.buffer) {
          drawBuffer(msg.buffer)
        }
      })

      // 2) Récupération initiale
      artClient.getBuffer()
        .then(buf => drawBuffer(buf))
        .catch(() => {})

      // 3) Polling régulier toutes les 200 ms
      pollingInterval = setInterval(() => {
        artClient.getBuffer()
          .then(buf => drawBuffer(buf))
          .catch(() => {})
      }, 100)
    }
  })

  onBeforeUnmount(() => {
    // Arrêt du polling
    if (pollingInterval) {
      clearInterval(pollingInterval)
      pollingInterval = null
    }
    // Fermeture propre du client (WS)
    artClient.close()
    isSubscribed = false
  })

  return { strokes, objects }
}
