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

  // 2️⃣ Brushes par canal (brush1.png → canal 1, brush2.png → canal 2, brush3.png → canal 3)
  const brushModules = import.meta.glob<string>(
    '~/assets/modules/4/images/brushes/brush*.png',
    { eager: true, as: 'url' }
  )

  const brushCanvases: Record<string, HTMLImageElement[]> = {
    '1': [],
    '2': [],
    '3': []
  }

  for (const [path, url] of Object.entries(brushModules)) {
    const fileName = path.split('/').pop()!
    const img = new Image()
    img.src = url
    if (fileName === 'brush1.png') {
      brushCanvases['1'].push(img)
    } else if (fileName === 'brush2.png') {
      brushCanvases['2'].push(img)
    } else if (fileName === 'brush3.png') {
      brushCanvases['3'].push(img)
    }
  }

  // 3️⃣ Stockage local
  const strokes = ref<Stroke[]>([])
  const objects = ref<ArtObject[]>([])

  // 4️⃣ Dessin
  const scale = 3
  function drawStroke(ctx: CanvasRenderingContext2D, s: Stroke) {
    const imgs = brushCanvases[s.tool_id] || []
    if (!imgs.length) return
    const img = imgs[0]  // un seul brush par canal
    const px = s.x * scale
    const py = s.y * scale
    const size = (s.size || 5) * scale
    const ang = s.angle || 0

    ctx.save()
    ctx.translate(px, py)
    ctx.rotate(ang)
    ctx.drawImage(img, -size / 2, -size / 2, size, size)
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

    // attendre que tous les brushes soient chargés
    const allBrushImages = Object.values(brushCanvases).flat()
    Promise.all(
      allBrushImages.map(img =>
        img.complete
          ? Promise.resolve()
          : new Promise<void>(res => { img.onload = () => res() })
      )
    ).then(() => {
      console.log('✅ Brushes chargés par canal')
    })

    artClient.onMessage(msg => {
      if (msg.action === 'get_buffer' && msg.buffer) {
        drawBuffer(msg.buffer)
      }
    })

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
    if (intervalId !== null) clearInterval(intervalId)
    artClient.close()
  })

  return { strokes, objects }
}
