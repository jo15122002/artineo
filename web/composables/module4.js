import { useRuntimeConfig } from '#app'
import { onBeforeUnmount } from 'vue'

export default function use4kinect(canvasRef) {
    const { public: { wsUrl } } = useRuntimeConfig()
    const moduleId = 4

    let ws
    let animationId

    const imgModules = import.meta.glob(
        '~/assets/modules/4/images/*.png',
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

    // 1️⃣ Ouverture du WS
    function setupWebSocket() {
        ws = new WebSocket(`${wsUrl}/ws`)
        ws.onopen = () => console.log('4KINECT WS ouverte')
        ws.onmessage = msg => {
            const data = JSON.parse(msg.data)
            if (data.action === 'get_buffer' && data.buffer.tool) {
                console.log('buffer', data.buffer)
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
        const scale = 3 // même zoom que dans le Python
        const W = canvas.width, H = canvas.height

        // Fond blanc
        ctx.fillStyle = '#ffffff'
        ctx.fillRect(0, 0, W, H)

        // Pour chaque stroke : un cercle (approx brush)
        buf.strokes.forEach(s => {
            ctx.beginPath()
            ctx.arc(
                s.x * scale,
                s.y * scale,
                (s.size || 5) * scale,
                0, Math.PI * 2
            )
            ctx.fillStyle = `rgb(${s.color[0]},${s.color[1]},${s.color[2]})`
            ctx.fill()
        })

        // (optionnel) superposer objets
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
        setupWebSocket()
        requestBuffer()
        animationId = setInterval(requestBuffer, 100) // plus fluide
    }

    onBeforeUnmount(() => {
        ws?.close()
        clearInterval(animationId)
    })
}