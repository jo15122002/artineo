// web/composables/use1ir.js
import { useRuntimeConfig } from '#app'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

export default function use1ir() {
    const { public: { apiUrl } } = useRuntimeConfig()
    const serverUrl = apiUrl

    // paramètres calibrage reçus depuis le serveur
    const realDiameter = ref(6)    // en cm, valeur par défaut
    const focalLength = ref(400)     // en pixels, valeur par défaut
    const backgroundPath = ref('tableau.png')   // chemin du PNG plein écran

    // état du module
    const x = ref(0), y = ref(0), diamPx = ref(1), z = ref(0)
    const hue = computed(() => (x.value / 320) * 360)      // 0–360°
    const sat = computed(() => (y.value / 240) * 200 + 50) // 50–250%
    const bright = computed(() => Math.min(200, 100 * (focalLength.value * realDiameter.value) / (diamPx.value || 1)))

    // filtre CSS à appliquer
    const filterStyle = computed(() =>
        `hue-rotate(${hue.value}deg) saturate(${sat.value}%) brightness(${bright.value}%)`
    )

    let ws

    function fetchConfig() {
        return fetch(`${serverUrl}/config?module=1`)
            .then(r => r.json())
            .then(json => {
                const cfg = json.config
                if (cfg.realDiameter) realDiameter.value = cfg.realDiameter
                if (cfg.focalLength) focalLength.value = cfg.focalLength
                // if (cfg.background) backgroundPath.value = cfg.background
            })
    }

    function setupWebSocket() {
        ws = new WebSocket(`ws://${serverUrl.replace(/^https?:\/\//, '')}/ws`)
        ws.onopen = () => console.log('IR module WS ouvert')
        ws.onmessage = e => {
            const msg = JSON.parse(e.data)
            if (msg.action === 'get_buffer') {
                const buf = msg.buffer
                x.value = buf.x
                y.value = buf.y
                diamPx.value = buf.diameter
                // calcul de la distance z en cm
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
        await fetchConfig()
        setupWebSocket()
        requestBuffer()
        // raffraîchir toutes les 100 ms
        const id = setInterval(requestBuffer, 100)
        onBeforeUnmount(() => {
            clearInterval(id)
            ws && ws.close()
        })
    })

    return { backgroundPath, filterStyle }
}
