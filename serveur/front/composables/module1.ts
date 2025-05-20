// front/composables/module1.ts
import { useNuxtApp } from '#app'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { BufferPayload } from '~/utils/ArtineoClient'

export default function useModule1() {
  // 1) Stub en SSR
  if (!process.client) {
    const stub = ref<any>(null)
    return {
      backgroundPath: stub,
      filterStyle: stub,
      x: stub,
      y: stub,
      diamPx: stub,
      fps: stub,
    }
  }

  const moduleId = 1
  const { $artineo } = useNuxtApp()
  const client = $artineo(moduleId)

  // 2) refs d’état
  const backgroundPath = ref<string>('')
  const x              = ref(0)
  const y              = ref(0)
  const diamPx         = ref(1)
  const fps            = ref(10)   // valeur par défaut

  // 3) calcul du filtre CSS
  const frameH = 240, minB = 50, maxB = 150
  const bright = computed(() => {
    const pct = (1 - y.value / frameH) * (maxB - minB) + minB
    return Math.min(Math.max(pct, minB), maxB)
  })
  const hue = computed(() => (x.value / 320) * 360)
  const sat = computed(() => (y.value / 240) * 200 + 50)
  const filterStyle = computed(
    () => `hue-rotate(${hue.value}deg) saturate(${sat.value}%) brightness(${bright.value}%)`
  )

  // 4) gestion du polling
  let pollTimer: ReturnType<typeof setInterval> | null = null
  const startPolling = () => {
    // on nettoie l'ancien timer
    if (pollTimer) clearInterval(pollTimer)
    // on relance un nouveau à la nouvelle cadence
    const intervalMs = Math.round(1000 / fps.value)
    pollTimer = setInterval(async () => {
      try {
        const buf = await client.getBuffer()
        if (buf.x != null)      x.value      = buf.x
        if (buf.y != null)      y.value      = buf.y
        if (buf.diameter != null) diamPx.value = buf.diameter
      } catch (err) {
        console.warn('[Module1] getBuffer failed', err)
      }
    }, intervalMs)
    console.info(`[Module1] polling every ${intervalMs}ms (${fps.value} fps)`)
  }

  // on redémarre le polling dès que fps change
  watch(fps, () => {
    if (process.client) startPolling()
  })

  onMounted(async () => {
    // a) fetchConfig incluant fps et background
    try {
      const cfg = await client.fetchConfig()
      if (cfg.background) backgroundPath.value = cfg.background
      if (typeof cfg.fps === 'number' && cfg.fps > 0) {
        fps.value = cfg.fps
      }
    } catch (e) {
      console.error('[Module1] fetchConfig error', e)
    }

    // b) setup WebSocket pour recevoir les pushes
    client.onMessage((msg: any) => {
      if (msg.action === 'get_buffer') {
        const buf = msg.buffer as BufferPayload
        if (buf.x != null)      x.value      = buf.x
        if (buf.y != null)      y.value      = buf.y
        if (buf.diameter != null) diamPx.value = buf.diameter
      }
    })
    client.start()  // lance la supervision WS

    // c) conservation et démarrage du polling
    startPolling()
  })

  onBeforeUnmount(() => {
    if (pollTimer) clearInterval(pollTimer)
    client.close()
  })

  return {
    backgroundPath,
    filterStyle,
    x, y, diamPx,
    fps,   // expose la valeur de fps pour debug/UI
  }
}
