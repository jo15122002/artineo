// front/composables/module1.ts
import { useNuxtApp } from '#app'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
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
    }
  }

  const moduleId = 1
  const { $artineo } = useNuxtApp()
  if (typeof $artineo !== 'function') {
    throw new Error('Plugin $artineo non injecté — vérifie plugins/artineo.ts')
  }
  const client = $artineo(moduleId)

  // 2) refs
  const backgroundPath = ref<string>('')
  const x              = ref(0)
  const y              = ref(0)
  const diamPx         = ref(1)

  // 3) fps & interval dynamique
  const fps      = ref(1)           // valeur par défaut
  let pollTimer: number | undefined

  // 4) style calculé
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

  // 5) setup
  onMounted(async () => {
    // a) fetchConfig incluant fps
    try {
      const cfg = await client.fetchConfig()
      if (cfg.background)      backgroundPath.value = cfg.background
      if (typeof cfg.fps === 'number' && cfg.fps > 0) {
        fps.value = cfg.fps
      }
    } catch (e) {
      console.error('[Module1] fetchConfig error', e)
    }

    // b) gestion WebSocket push
    client.onMessage((msg: any) => {
      if (msg.action === 'get_buffer') {
        const buf = msg.buffer as BufferPayload
        x.value      = buf.x      ?? x.value
        y.value      = buf.y      ?? y.value
        diamPx.value = buf.diameter ?? diamPx.value
      }
    })

    // c) polling dynamique selon fps
    const pollIntervalMs = () => Math.round(1000 / fps.value)
    const apply = (buf: BufferPayload) => {
      x.value      = buf.x
      y.value      = buf.y
      diamPx.value = buf.diameter
    }

    // initial + fallback HTTP
    try {
      const buf0 = await client.getBuffer()
      apply(buf0)
    } catch {}

    // lance le polling
    pollTimer = window.setInterval(async () => {
      try {
        const buf = await client.getBuffer()
        apply(buf)
      } catch {
        // ignore
      }
    }, pollIntervalMs())
  })

  onBeforeUnmount(() => {
    if (pollTimer) clearInterval(pollTimer)
    client.close()
  })

  // 6) expose fps si besoin
  return {
    backgroundPath,
    filterStyle,
    x, y, diamPx,
    fps,              // optionnel, pour debug ou UI
  }
}
