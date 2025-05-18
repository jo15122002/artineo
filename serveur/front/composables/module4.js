// composables/use4kinect.js
import { useRuntimeConfig } from '#app'
import { ref, onBeforeUnmount } from 'vue'

export default function use4kinect(canvasRef) {
    const { public: { wsUrl } } = useRuntimeConfig()
    const moduleId = 4

    let ws = null
    let animationId = null

    // 1️⃣ Préchargement des sprites d'objets
    const imgModules = import.meta.glob(
        '~/assets/modules/4/images/objects/*.png',
        { eager: true, as: 'url' }
    )
    const objectImages = {}
    Object.entries(imgModules).forEach(([path, url]) => {
        const name = path.split('/').pop().replace('.png', '')
        const img = new Image()
        img.src = url
        objectImages[name] = img
    })

    // 2️⃣ Préchargement des brushes en niveaux de gris
    const brushModules = import.meta.glob(
        '~/assets/modules/4/images/brushes/*.png',
        { eager: true, as: 'url' }
    )
    const rawBrushImages = Object.values(brushModules).map(url => {
        const img = new Image()
        img.src = url
        return img
    })

    // 3️⃣ Mapping tool → couleur RGB
    const colorMap = {
        '1': [255, 0, 0],   // rouge
        '2': [0, 255, 0],   // vert
        '3': [0, 0, 255],   // bleu
    }

    // 4️⃣ Canvases tampon colorisés, un tableau par tool
    const brushCanvases = { '1': [], '2': [], '3': [] }

    function prepareBrushes() {
        rawBrushImages.forEach(img => {
            const cw = img.width, ch = img.height
            Object.entries(colorMap).forEach(([toolId, [r, g, b]]) => {
                const c = document.createElement('canvas')
                c.width = cw
                c.height = ch
                const ctx = c.getContext('2d')

                // dessiner le brush d’origine (niveau de gris)
                ctx.drawImage(img, 0, 0)
                const idata = ctx.getImageData(0, 0, cw, ch)
                const d = idata.data

                // remplacer le canal R/G/B puis alpha = luminosité
                for (let i = 0; i < d.length; i += 4) {
                    const lum = d[i]    // R=G=B=lum
                    d[i] = r          // R
                    d[i + 1] = g          // G
                    d[i + 2] = b          // B
                    d[i + 3] = lum        // alpha
                }
                ctx.putImageData(idata, 0, 0)
                brushCanvases[toolId].push(c)
            })
        })
        console.log('✅ Brushes prêts:',
            Object.entries(brushCanvases)
                .map(([t, arr]) => `${t}→${arr.length}`)
                .join(', ')
        )
    }

    // 5️⃣ Stockage local des strokes et objets
    const strokes = ref([])
    const objects = ref([])

    // 6️⃣ Fonctions de dessin individuelles
    const scale = 3
    function drawStroke(ctx, s) {
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

    function drawObject(ctx, o) {
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

    // 7️⃣ Gestion du buffer reçu (diffs)
    function drawBuffer(buf) {
        // Appliquer ajouts de strokes : assigner angle une seule fois
        if (buf.newStrokes) {
            buf.newStrokes.forEach(s => {
                if (!strokes.value.some(old => old.id === s.id)) {
                    // donner un angle aléatoire à la première apparition
                    if (s.angle === undefined) {
                        s.angle = Math.random() * Math.PI * 2
                    }
                    strokes.value.push(s)
                }
            })
        }
        // Appliquer suppressions de strokes
        if (buf.removeStrokes) {
            strokes.value = strokes.value.filter(s => !buf.removeStrokes.includes(s.id))
        }

        // Appliquer ajouts/suppressions d'objets
        if (buf.newObjects) {
            objects.value.push(...buf.newObjects)
        }
        if (buf.removeObjects) {
            objects.value = objects.value.filter(o => !buf.removeObjects.includes(o.id))
        }

        // Redessiner le canvas en entier
        const canvas = canvasRef.value
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        ctx.clearRect(0, 0, canvas.width, canvas.height)
        ctx.fillStyle = '#fff'
        ctx.fillRect(0, 0, canvas.width, canvas.height)

        strokes.value.forEach(s => drawStroke(ctx, s))
        objects.value.forEach(o => drawObject(ctx, o))

        // console.log('Strokes on canvas:', strokes.value.length)
    }

    // 8️⃣ WebSocket
    function setupWebSocket() {
        ws = new WebSocket(`${wsUrl}/ws`)
        ws.onopen = () => console.log('4KINECT WS ouverte')
        ws.onmessage = ev => {
            const msg = JSON.parse(ev.data)
            console.log('Action reçue:', msg)
            if (msg.action === 'get_buffer' && msg.buffer) {
                drawBuffer(msg.buffer)
            }
        }
        ws.onclose = () => setTimeout(setupWebSocket, 3000)
    }

    function requestBuffer() {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ module: moduleId, action: 'get' }))
        }
    }

    // 9️⃣ Initialisation
    if (process.client) {
        const loads = rawBrushImages.map(img =>
            new Promise(res => img.complete ? res() : img.onload = () => res())
        )
        Promise.all(loads).then(prepareBrushes)
        setupWebSocket()
        requestBuffer()
        animationId = setInterval(requestBuffer, 100)
    }

    // 🔟 Cleanup
    onBeforeUnmount(() => {
        ws?.close()
        clearInterval(animationId)
    })
}
