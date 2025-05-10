// web/composables/use1ir.js
import { useRuntimeConfig } from '#app'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

export default function use1ir() {
    const { public: { apiUrl } } = useRuntimeConfig()
    const serverUrl = apiUrl

    // calibration
    const realDiameter = ref(6)    // cm
    const focalLength = ref(400)   // px

    // état de la détection
    const x = ref(0)
    const y = ref(0)
    const diamPx = ref(1)
    const z = ref(0)

    // param debug via URL
    const showDebug = ref(false)

    // CSS filter
    const hue = computed(() => (x.value / 320) * 360)
    const sat = computed(() => (y.value / 240) * 200 + 50)
    const bright = computed(() =>
        Math.min(200, 100 * (focalLength.value * realDiameter.value) / (diamPx.value || 1))
    )
    const filterStyle = computed(() =>
        `hue-rotate(${hue.value}deg) saturate(${sat.value}%) brightness(${bright.value}%)`
    )

    let ws, timerId

    function fetchConfig() {
        return fetch(`${serverUrl}/config?module=1`)
            .then(r => r.json())
            .then(json => {
                const cfg = json.config
                if (cfg.realDiameter) realDiameter.value = cfg.realDiameter
                if (cfg.focalLength) focalLength.value = cfg.focalLength
                if (cfg.background) backgroundPath.value = cfg.background
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
        // 1) detect debug=1 dans l'URL
        const params = new URLSearchParams(window.location.search)
        showDebug.value = params.get('debug') === '1'

        // 2) lancement WebSocket + config
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
        filterStyle,
        showDebug,
        x, y, diamPx
    }
}
