import { useRuntimeConfig } from '#app'
import { onBeforeUnmount, onMounted } from 'vue'

export default function use4kinect(canvasRef) {
    const { public: { wsUrl } } = useRuntimeConfig()
    const moduleId = 4

    let ws
    let animationId

    const imgModules = import.meta.glob(
        '~/assets/modules/4/images/objects/*.png',
        { eager: true, as: 'url' }
    )

    const brushModules = import.meta.glob(
        '~/assets/modules/4/images/brushes/*.png',
        { eager: true, as: 'url' }
    )

    const objectSprites = {}
    const objectImages  = {}

    Object.entries(imgModules).forEach(([path, url]) => {
        const filename = path.split('/').pop()          // ex. "Fond_mer2.png"
        const name     = filename.replace('.png', '')   // ex. "Fond_mer2"
        objectSprites[name] = url

        // Pré-création de l'Image
        const img = new Image()
        img.src = url
        objectImages[name] = img
    })

    const rawBrushImages = Object.values(brushModules).map(url => {
        const img = new Image()
        img.src = url
        return img
    })

    const brushCanvases = []
    function prepareBrushes() {
        rawBrushImages.forEach(img => {
        const cw = img.width, ch = img.height
        const c = document.createElement('canvas')
        c.width = cw; c.height = ch
        const ctx = c.getContext('2d')
        ctx.drawImage(img, 0, 0)
        const id = ctx.getImageData(0, 0, cw, ch)
        const d  = id.data
        for (let i = 0; i < d.length; i += 4) {
            const lum = d[i]            // R=G=B=lum
            d[i]   = 255                // R
            d[i+1] = 0                  // G
            d[i+2] = 0                  // B
            d[i+3] = lum                // alpha = niveau de gris
        }
        ctx.putImageData(id, 0, 0)
        brushCanvases.push(c)
        })
        console.log(`✅ ${brushCanvases.length} brushes prêts`)
    }

    // 1️⃣ Ouverture du WS
    function setupWebSocket() {
        ws = new WebSocket(`${wsUrl}/ws`)
        ws.onopen = () => console.log('4KINECT WS ouverte')
        ws.onmessage = msg => {
            const data = JSON.parse(msg.data)
            if (data.action === 'get_buffer' && data.buffer.tool) {
                const canvas = canvasRef.value
                console.log(data.buffer);
                // console.log('buffer', data.buffer)
                drawBuffer(data.buffer)
            }
        }
        ws.onclose = () => setTimeout(setupWebSocket, 3000)
    }

    // 2️⃣ Demande régulière du buffer
    function requestBuffer() {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ module: moduleId, action: 'get' }))
        }
    }

    // 3️⃣ Dessin sur le canvas
    function drawBuffer(buf) {
        const canvas = canvasRef.value
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        const scale = 3;
        const W = canvas.width, H = canvas.height

        // Fond blanc
        ctx.fillStyle = '#ffffff'
        ctx.fillRect(0, 0, W, H)

        if (brushCanvases.length) {
            buf.strokes.forEach(s => {
              const bc = brushCanvases[
                Math.floor(Math.random() * brushCanvases.length)
              ]
              const px    = s.x * scale
              const py    = s.y * scale
              const size  = (s.size || 5) * scale
              const angle = Math.random() * Math.PI * 2
      
              ctx.save()
              ctx.translate(px, py)
              ctx.rotate(angle)
              ctx.drawImage(bc, -size/2, -size/2, size, size)
              ctx.restore()
            })
          }

        buf.objects.forEach(o => {
        const img = objectImages[o.shape]
        if (img && img.complete) {
            const w = o.w * scale
            const h = o.h * scale
            const x = o.cx * scale - w/2
            const y = o.cy * scale - h/2
            ctx.drawImage(img, x, y, w, h)
        } else {
            // placeholder
            ctx.fillStyle = '#000'
            ctx.fillRect(o.cx*scale - 5, o.cy*scale - 5, 10, 10)
        }
        })
    }

    // 4️⃣ Lancement au montage
    if (process.client) {
        console.log('4Kinect module monté')
        const loads = rawBrushImages.map(img => new Promise(res => {
            if (img.complete) res()
            else img.onload = () => res()
        }))
        Promise.all(loads).then(() => prepareBrushes())

        setupWebSocket()
        requestBuffer()
        animationId = setInterval(requestBuffer, 100) // plus fluide
    }

    onBeforeUnmount(() => {
        ws?.close()
        clearInterval(animationId)
    })
}