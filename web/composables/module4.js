import { useRuntimeConfig } from '#app'
import { onBeforeUnmount } from 'vue'

export default function use4kinect(canvasRef) {
    const { public: { apiBase } } = useRuntimeConfig()
    const serverUrl = apiBase.replace(/^http/, 'ws') // ws://…
    const moduleId = 4

    let ws
    let animationId

    // 1️⃣ Ouverture du WS
    function setupWebSocket() {
        ws = new WebSocket(`${serverUrl}/ws`)
        ws.onopen = () => console.log('4KINECT WS ouverte')
        ws.onmessage = msg => {
            const data = JSON.parse(msg.data)
            if (data.action === 'get_buffer' && data.buffer.tool) {
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
            // placeholder : un petit carré noir
            ctx.fillStyle = '#000'
            ctx.fillRect(o.cx * scale - 5, o.cy * scale - 5, 10, 10)
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