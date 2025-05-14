import { useNuxtApp } from '#app'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { BufferPayload } from '~/utils/ArtineoClient'

export default function useModule1() {
  // ⚠️ Cette ligne ne s’exécute qu’en client
  if (!process.client) {
    // retourne des refs vides / stubs en SSR
    const empty = ref<any>(null)
    return { backgroundPath: empty, filterStyle: empty, x: empty, y: empty, diamPx: empty }
  }

  const moduleId = 1
  const { $artineo } = useNuxtApp()

  if (typeof $artineo !== 'function') {
    throw new Error('Plugin $artineo non injecté — voir plugins/artineo.ts')
  }

  const client = $artineo(moduleId)

  // tes refs
  const backgroundPath = ref<string>('')
  const x  = ref(0)
  const y  = ref(0)
  const diamPx = ref(1)

  // ton calcul de filterStyle…
  const frameH = 240, minB = 50, maxB = 150
  const bright = computed(() => {
    const pct = (1 - y.value / frameH) * (maxB - minB) + minB
    return Math.min(Math.max(pct, minB), maxB)
  })
  const hue = computed(() => (x.value / 320) * 360)
  const sat = computed(() => (y.value / 240) * 200 + 50)
  const filterStyle = computed(() =>
    `hue-rotate(${hue.value}deg) saturate(${sat.value}%) brightness(${bright.value}%)`
  )

  let pollId: number

  onMounted(async () => {
    // 1️⃣ config initiale
    try {
      const cfg = await client.fetchConfig()
      if (cfg.background) backgroundPath.value = cfg.background
      // … realDiameter, focalLength si besoin
    } catch (e) {
      console.error('[Module1] fetchConfig', e)
    }

    // 2️⃣ écoute WS
    client.onMessage((msg: any) => {
      if (msg.action === 'get_buffer') {
        const buf = msg.buffer as BufferPayload
        x.value      = buf.x      ?? x.value
        y.value      = buf.y      ?? y.value
        diamPx.value = buf.diameter ?? diamPx.value
      }
    })

    // 3️⃣ fallback polling HTTP
    const apply = (buf: BufferPayload) => {
      x.value = buf.x; y.value = buf.y; diamPx.value = buf.diameter
    }
    try {
      const init = await client.getBuffer()
      apply(init)
    } catch {}
    pollId = window.setInterval(async () => {
      try {
        const buf = await client.getBuffer()
        apply(buf)
      } catch {}
    }, 100)
  })

  onBeforeUnmount(() => {
    clearInterval(pollId)
    client.close()
  })

  return { backgroundPath, filterStyle, x, y, diamPx }
}
