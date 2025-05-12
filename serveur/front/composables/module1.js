// web/composables/use1ir.js
import { useRuntimeConfig } from '#app'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

export default function use1ir() {
    const { public: { apiUrl, wsUrl } } = useRuntimeConfig()
    const backgroundPath = ref('tableau.png')

    // calibration
    const realDiameter = ref(6)    // cm
    const focalLength = ref(400)   // px

    // état de la détection
    const x = ref(0)
    const y = ref(0)
    const diamPx = ref(1)
    const z = ref(0)

    // debug URL
    const showDebug = ref(false)

    // --- NOUVEAU : paramètres pour le brightness vertical ---
    const frameHeight = 240   // px, ajustez si votre hauteur change
    const minBrightPct = 50    // brightness() en bas de l'écran
    const maxBrightPct = 150   // brightness() en haut de l'écran

    // calcul de la luminosité pivotée au milieu :
    const bright = computed(() => {
        // ratio de 0 (top) → 1 (bottom)
        const r = y.value / frameHeight
        // on veut : at r=0.5 → 100%, at r=0 → maxBrightPct, at r=1 → minBrightPct
        const v = (1 - r) * (maxBrightPct - minBrightPct) + minBrightPct
        // clamp entre min et max
        return Math.max(minBrightPct, Math.min(maxBrightPct, v))
    })

    // couleur & saturation inchangées
    const hue = computed(() => (x.value / 320) * 360)
    const sat = computed(() => (y.value / 240) * 200 + 50)

    // filtre CSS final
    const filterStyle = computed(() =>
        `hue-rotate(${hue.value}deg) saturate(${sat.value}%) brightness(${bright.value}%)`
    )

    let ws, timerId

    function fetchConfig() {
        return fetch(`${apiUrl}/config?module=1`)
            .then(r => r.json())
            .then(json => {
                const cfg = json.config
                if (cfg.realDiameter) realDiameter.value = cfg.realDiameter
                if (cfg.focalLength) focalLength.value = cfg.focalLength
                if (cfg.background) backgroundPath.value = cfg.background
            })
    }

    function setupWebSocket() {
        ws = new WebSocket(`${wsUrl}/ws`)
        ws.onopen = () => console.log('IR module WS ouvert')
        ws.onmessage = e => {
            const msg = JSON.parse(e.data)
            if (msg.action === 'get_buffer') {
                const buf = msg.buffer
                x.value = buf.x
                y.value = buf.y
                diamPx.value = buf.diameter
                z.value = (focalLength.value * realDiameter.value) / (diamPx.value || 1)
            }
        }
        ws.onclose = () => setTimeout(setupWebSocket, 2000)
    }

    function requestBuffer() {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ module: 1, action: 'get' }))
        }
    }

    onMounted(async () => {
        // détection ?debug=1
        showDebug.value = new URLSearchParams(window.location.search).get('debug') === '1'

        await fetchConfig()
        setupWebSocket()
        requestBuffer()
        timerId = setInterval(requestBuffer, 100)
    })

    onBeforeUnmount(() => {
        clearInterval(timerId)
        ws && ws.close()
    })

    return {
        backgroundPath,
        filterStyle,
        showDebug,
        x, y, diamPx
    }
}
