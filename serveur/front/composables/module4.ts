// File: serveur/front/composables/module4.ts
import type { Ref } from 'vue'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
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
export default function use4kinect(canvasRef: Ref<HTMLCanvasElement | null>, stepRef: Ref<number>) {
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

  // 2️⃣bis load mask image
  const maskModules = import.meta.glob<string>(
    '~/assets/modules/4/images/masks/mask.png',
    { eager: true, as: 'url' }
  )

  // on récupère la première (et seule) URL disponible :
  const maskPaths = Object.values(maskModules)
  if (maskPaths.length === 0) {
    console.error('[Module4] Aucun mask trouvé via glob')
  }
  const maskPath = maskPaths[0]!

  // offscreen pour le mask
  const maskCanvas = document.createElement('canvas')
  let maskCtx: CanvasRenderingContext2D | null = null

  const maskImage = new Image()
  maskImage.src = maskPath
  maskImage.onload = () => console.log('[Module4] Mask loaded:', maskPath)
  maskImage.onerror = e => console.error('[Module4] Failed to load mask image:', maskPath, e)

  // 3️⃣ map button IDs to RGBA overlays
  const buttonColors: Record<number, string> = {
    1: 'rgba(83, 160, 236, 0.2)',
    2: 'rgba(252, 191, 0, 0.2)',
  }
  let currentButton = 1  // default

  // 4️⃣ local state
  const strokes = ref<Stroke[]>([])
  const objects = ref<ArtObject[]>([])
  const backgrounds = ref<ArtObject[]>([])
  const scale = 3

  // dès qu’on change d’étape, on vide les strokes si on n’est plus en step 1
  watch(stepRef, newStep => {
    if (newStep !== 1) {
      strokes.value = []
    }
  })

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

    const canvas = canvasRef.value!
    const ctx = canvas.getContext('2d')!

    // initialise / recalcule la taille du maskCanvas
    if (!maskCtx
      || maskCanvas.width !== canvas.width
      || maskCanvas.height !== canvas.height
    ) {
      maskCanvas.width = canvas.width
      maskCanvas.height = canvas.height
      maskCtx = maskCanvas.getContext('2d')
    }

    // 7.1) button event
    if (typeof buf.button === 'number') {
      currentButton = buf.button
    }

    // 7.2) add strokes
    if (buf.newStrokes && stepRef.value === 1) {
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
      console.log('[Artineo][Kinect] received new backgrounds', buf.newBackgrounds)
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

    // 1️⃣ clear + fond blanc
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    // 3️⃣ mask découpé aux brushes, sur offscreen
    if (maskCtx && maskImage.complete && strokes.value.length > 0) {
      // a) clear
      maskCtx.clearRect(0, 0, maskCanvas.width, maskCanvas.height)

      // b) draw all your brushes in source-over
      maskCtx.globalCompositeOperation = 'source-over'
      const mCtx = maskCtx!
      strokes.value.forEach(s => {
        const img = brushImages[s.tool_id]
        if (!img || !img.complete) return
        const px = s.x * scale
        const py = s.y * scale
        const size = (s.size ?? 5) * scale * 1.5
        const ang = s.angle ?? 0

        mCtx.save()
        mCtx.translate(px, py)
        mCtx.rotate(ang)
        mCtx.drawImage(img, -size / 2, -size / 2, size, size)
        mCtx.restore()
      })

      // c) passe en source-in et dessine le mask image
      maskCtx.globalCompositeOperation = 'source-in'
      maskCtx.drawImage(maskImage, 0, 0, maskCanvas.width, maskCanvas.height)

      // d) reviens en source-over
      maskCtx.globalCompositeOperation = 'source-over'

      // e) colle le résultat sur le canvas principal
      ctx.drawImage(maskCanvas, 0, 0)
    }

    // 2️⃣ backgrounds
    backgrounds.value.forEach(b => drawBackground(ctx, b))

    // 4️⃣ objets
    objects.value.forEach(o => drawObject(ctx, o))

    // 5️⃣ overlay couleur
    const overlay = buttonColors[currentButton] || buttonColors[1]
    ctx.fillStyle = overlay
    ctx.fillRect(0, 0, canvas.width, canvas.height)
  }


  // ─────────────── 9️⃣ fonction d’ajout d’image ───────────────
  /**
   * Ajoute sur le canvas, à la position (cx, cy), l’image `shape`.
   * @param shape  Nom de l’image (clé dans objectImages)
   * @param cx     Abscisse en coordonnées art (non-scalées)
   * @param cy     Ordonnée en coordonnées art (non-scalées)
   * @param w      Largeur en coordonnées art (optionnel, défaut = largeur naturelle/scale)
   * @param h      Hauteur en coordonnées art (optionnel, défaut = hauteur naturelle/scale)
   * @param angle  Rotation en radians (optionnel)
   * @param scale  Facteur de mise à l’échelle interne (optionnel)
   */
  function addImage(
    shape: string,
    cx: number,
    cy: number,
    w?: number,
    h?: number,
    angle = 0,
    scale = 1
  ) {
    const img = objectImages[shape];
    // dimensions par défaut en « unités art »
    const defaultW = img ? img.naturalWidth / (scale * 3) : 50;
    const defaultH = img ? img.naturalHeight / (scale * 3) : 50;

    const newObj: ArtObject = {
      id: Date.now().toString() + Math.random().toString(),  // ou Date.now() + Math.random()
      shape,
      cx,
      cy,
      w: w ?? defaultW,
      h: h ?? defaultH,
      angle,
      scale
    };

    if (shape.startsWith('landscape_')) {
      // si c'est un background, on le remplace
      const existingIndex = backgrounds.value.findIndex(b => b.shape === shape);
      if (existingIndex !== -1) {
        backgrounds.value[existingIndex] = newObj;
      } else {
        backgrounds.value.push(newObj);
      }
    }
    else {
      objects.value.push(newObj);
    }

    // on redessine immédiatement
    // on passe un buffer vide pour ne rien supprimer…
    drawBuffer({});
  }

  const keyBindings: Record<string,
    {
      shape: string | undefined;
      cx: number | undefined;
      cy: number | undefined,
      w: number | undefined,
      h: number | undefined,
      button: number | undefined
    }
  > = {
    a: {
      shape: 'landscape_fields', cx: 50, cy: 80,
      w: undefined,
      h: undefined,
      button: undefined
    },
    p: {
      shape: 'landscape_sea', cx: 200, cy: 150,
      w: undefined,
      h: undefined,
      button: undefined
    },
    o: {
      shape: 'medium_lighthouse', cx: 250, cy: 60, w: 90, h: 100,
      button: undefined
    },
    z: {
      shape: 'medium_mill', cx: 150, cy: 67, w: 90, h: 90,
      button: undefined
    },
    i: {
      shape: 'small_boat', cx: 60, cy: 100, w: 80, h: 60,
      button: undefined
    },
    1: { shape: undefined, cx: undefined, cy: undefined, w: undefined, h: undefined, button: 1 },
    2: { shape: undefined, cx: undefined, cy: undefined, w: undefined, h: undefined, button: 2 }
  };

  function onKeydown(ev: KeyboardEvent) {
    const binding = keyBindings[ev.key];
    if (binding.shape) {
      ev.preventDefault();
      addImage(binding.shape, binding.cx!, binding.cy!, binding.w, binding.h);
    } else if (binding.button) {
      ev.preventDefault();
      currentButton = binding.button;
      drawBuffer({ button: currentButton });  // redessine avec la nouvelle couleur
    }
  }

  // 8️⃣ WebSocket + HTTP fallback polling
  let pollingIntervalKinect: ReturnType<typeof setInterval> | null = null
  let pollingIntervalButton: ReturnType<typeof setInterval> | null = null
  let isKinectSubscribed = false
  let isButtonSubscribed = false

  onMounted(async () => {
    console.log('Module 4: Kinect + Button')
    startTimer()
    // subscribe to Kinect updates
    if (!isKinectSubscribed) {
      isKinectSubscribed = true
      artClientKinect.onMessage((msg: any) => {
        if (msg.action === 'get_buffer' && msg.buffer) {
          console.log('[Artineo][Kinect] received buffer', msg.buffer)
          drawBuffer(msg.buffer)
        }
      })

      artClientKinect.getBuffer()
        .then((buf: any) => drawBuffer(buf))
        .catch((e: any) => console.error('[Artineo][Kinect] init error', e))

      pollingIntervalKinect = setInterval(() => {
        artClientKinect.getBuffer()
          .then((buf: any) => drawBuffer(buf))
          .catch(() => { })
      }, 100)
    }

    // subscribe to Button updates
    if (!isButtonSubscribed) {
      isButtonSubscribed = true
      artClientButton.onMessage((msg: any) => {
        if (msg.action === 'get_buffer' && msg.buffer) {
          drawBuffer(msg.buffer)
        }
      })

      artClientButton.getBuffer()
        .then((buf: any) => drawBuffer(buf))
        .catch((e: any) => console.error('[Artineo][Button] init error', e))

      pollingIntervalButton = setInterval(() => {
        artClientButton.getBuffer()
          .then((buf: any) => drawBuffer(buf))
          .catch(() => { })
      }, 100)
    }

    window.addEventListener('keydown', onKeydown);
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

    window.removeEventListener('keydown', onKeydown);
  })

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
    const h = hex.replace('#', '')
    const bigint = parseInt(h, 16)
    return {
      r: (bigint >> 16) & 0xFF,
      g: (bigint >> 8) & 0xFF,
      b: bigint & 0xFF,
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
      const { p: p1, color: c1 } = colorStops[i + 1]
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

  return { strokes, objects, backgrounds, timerColor, timerText, timerSeconds, startTimer }
}
