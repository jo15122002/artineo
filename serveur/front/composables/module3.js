import { useRuntimeConfig } from '#app'
import { onBeforeUnmount } from 'vue'

export default function use3rfid() {
    const { public: { apiUrl, wsUrl } } = useRuntimeConfig()
    const moduleId = 3

    let ws
    let _lastBackgroundSet = null
    let _lastBuffer = { current_set: 1, uid1: null, uid2: null, uid3: null, button_pressed: false }
    let assignments, wanted, answers

    // 1️⃣ Récupère la config et initialise tout
    async function fetchConfig() {
        const res = await fetch(`${apiUrl}/config?module=${moduleId}`)
        const json = await res.json()
        assignments = json.config.assignments
        answers = json.config.answers

        wanted = {
            lieux: Object.entries(assignments.lieux || {}),
            couleurs: Object.entries(assignments.couleurs || {}),
            emotions: Object.entries(assignments.emotions || {})
        }

        setupWebSocket()
        requestBuffer()
        changeBackground(1)
        setInterval(requestBuffer, 1000)
    }

    // 2️⃣ WebSocket pour recevoir le buffer
    function setupWebSocket() {
        ws = new WebSocket(`${wsUrl}/ws`)
        ws.onopen = () => console.log('3RFID WS ouverte')
        ws.onmessage = e => {
            const msg = JSON.parse(e.data)
            if (msg.action === 'get_buffer') updateBlobs(msg.buffer)
        }
        ws.onclose = () => setTimeout(setupWebSocket, 3000)
    }

    // 3️⃣ Envoi la requête get
    function requestBuffer() {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ module: moduleId, action: 'get' }))
        }
    }

    // 4️⃣ Met à jour texte + déclenche coloration si bouton
    function updateBlobs(buf) {
        console.log('updateBlobs', buf)
        ['blob1', 'blob2', 'blob3'].forEach((id, i) => {
            const el = document.getElementById(id)
            const uid = buf[`uid${i + 1}`]
            const arr = i === 0 ? wanted.lieux : i === 1 ? wanted.couleurs : wanted.emotions
            const word = uid ? (arr.find(([w, u]) => u === uid) || [])[0] : ''
            el.textContent = word || 'Aucun'
        })

        if (buf.current_set !== _lastBuffer.current_set) {
            changeBackground(buf.current_set)
        }
        if (buf.button_pressed) {
            highlightBlobs(buf)
        }
        _lastBuffer = buf
    }

    // 5️⃣ Coloration “LED” via background-color
    function highlightBlobs(buf = _lastBuffer) {
        const idx = (buf.current_set || 1) - 1
        ['blob1', 'blob2', 'blob3'].forEach((id, i) => {
            const el = document.getElementById(id)
            const uid = buf[`uid${i + 1}`]
            const key = i === 0 ? 'lieu' : i === 1 ? 'couleur' : 'emotion'

            const color = !uid
                ? '#FFA500'
                : uid.toLowerCase() === answers[idx][key].toLowerCase()
                    ? '#00FF00'
                    : '#FF0000'

            el.style.backgroundColor = color
            // si tu veux changer la couleur du texte aussi :
            el.style.color = color === '#FF0000' ? '#fff' : '#000'
        })
    }

    // 6️⃣ Changement du PNG de fond
    function changeBackground(set) {
        if (set === _lastBackgroundSet) return
        _lastBackgroundSet = set
        let backgroundDiv = document.getElementById('background')

        fetch(`${apiUrl}/getAsset?module=${moduleId}&path=tableau${set}.png`)
            .then(r => r.blob())
            .then(b => {
                backgroundDiv.style.backgroundImage = `url(${URL.createObjectURL(b)})`
            })
            .catch(console.error)
    }

    // Lancement côté client
    if (process.client) {
        fetchConfig()
    }

    // Nettoyage
    onBeforeUnmount(() => {
        if (ws) ws.close()
    })
}