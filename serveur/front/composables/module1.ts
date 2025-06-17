// File: serveur/front/composables/module1.ts
import { useNuxtApp } from '#app'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { BufferPayload } from '~/utils/ArtineoClient'

export default function useModule1() {
  // SSR stub
  if (!process.client) {
    const stub = ref<any>(null)
    return {
      backgroundPath: stub,
      filterStyle: stub,
      x: stub,
      y: stub,
      diamPx: stub,
      inZone: stub,
      entryTime: stub,
      responseAlreadyValidated: stub,
      timerColor: stub,
      timerText: stub
    }
  }

  const moduleId = 1
  const { $artineo } = useNuxtApp()
  if (typeof $artineo !== 'function') {
    throw new Error('Plugin $artineo non injecté — vérifie plugins/artineo.ts')
  }
  const client = $artineo(moduleId)

  // reactive state
  const backgroundPath = ref<string>('')
  const x = ref(0)
  const y = ref(0)
  const diamPx = ref(1)

  // "bonne réponse" logic
  const goodResponsePosition = { x: 160, y: 120 }
  const goodResponseZoneSize = 30
  const goodResponseStayTime = 2.0
  const inZone = ref(false)
  let entryTime: number | null = null
  let responseAlreadyValidated = false

  // fps & polling
  const fps = ref(10)
  let pollTimer: number | undefined

  // CSS filter for feedback
  const filterStyle = computed(() => {
    const dx = x.value - goodResponsePosition.x
    const dy = y.value - goodResponsePosition.y
    let hueVal = (dx / goodResponsePosition.x) * 180
    hueVal = Math.max(-180, Math.min(180, hueVal))
    const refDiam = goodResponseZoneSize
    let satVal = 100 + ((diamPx.value - refDiam) / refDiam) * 100
    satVal = Math.max(0, Math.min(200, satVal))
    let brightVal = 100 - (dy / goodResponsePosition.y) * 50
    brightVal = Math.max(50, Math.min(150, brightVal))
    return `hue-rotate(${hueVal.toFixed(1)}deg)
            saturate(${satVal.toFixed(0)}%)
            brightness(${brightVal.toFixed(0)}%)`
  })

  // ────────────────────────────────────────────────────────────────────────────
  // TIMER logic
  // ────────────────────────────────────────────────────────────────────────────
  const TIMER_DURATION = 60 // secondes
  const timerSeconds = ref<number>(TIMER_DURATION)
  let timerInterval: number | undefined

  function startTimer() {
    if (timerInterval) clearInterval(timerInterval)
    timerSeconds.value = TIMER_DURATION
    timerInterval = window.setInterval(() => {
      timerSeconds.value = Math.max(timerSeconds.value - 1, 0)
      if (timerSeconds.value === 0 && timerInterval) {
        clearInterval(timerInterval)
      }
    }, 1000)
  }

  function pauseTimer() {
    if (timerInterval) {
      clearInterval(timerInterval)
      timerInterval = undefined
    }
  }

  function resumeTimer() {
    if (!timerInterval && timerSeconds.value > 0) {
      timerInterval = window.setInterval(() => {
        timerSeconds.value = Math.max(timerSeconds.value - 1, 0)
        if (timerSeconds.value === 0 && timerInterval) {
          clearInterval(timerInterval)
        }
      }, 1000)
    }
  }

  function resetTimer() {
    pauseTimer()
    timerSeconds.value = TIMER_DURATION
  }

  function hexToRgb(hex: string) {
    const h = hex.replace('#', '')
    const bigint = parseInt(h, 16)
    return {
      r: (bigint >> 16) & 0xff,
      g: (bigint >> 8) & 0xff,
      b: bigint & 0xff
    }
  }

  function rgbToHex(r: number, g: number, b: number) {
    const to2 = (x: number) => x.toString(16).padStart(2, '0')
    return `#${to2(r)}${to2(g)}${to2(b)}`
  }

  function lerp(a: number, b: number, t: number) {
    return a + (b - a) * t
  }

  const colorStops = [
    { p: 1.0, color: '#2626FF' },
    { p: 0.6, color: '#FA81C3' },
    { p: 0.3, color: '#FA4923' }
  ] as const

  const timerColor = computed(() => {
    const pct = timerSeconds.value / TIMER_DURATION
    for (let i = 0; i < colorStops.length - 1; i++) {
      const { p: p0, color: c0 } = colorStops[i]
      const { p: p1, color: c1 } = colorStops[i + 1]
      if (pct <= p0 && pct >= p1) {
        const t = (p0 - pct) / (p0 - p1)
        const a = hexToRgb(c0), b = hexToRgb(c1)
        return rgbToHex(
          Math.round(lerp(a.r, b.r, t)),
          Math.round(lerp(a.g, b.g, t)),
          Math.round(lerp(a.b, b.b, t))
        )
      }
    }
    return colorStops[colorStops.length - 1].color
  })

  const timerText = computed(() => {
    const m = Math.floor(timerSeconds.value / 60)
    const s = timerSeconds.value % 60
    return `${m}:${String(s).padStart(2, '0')}`
  })

  // ────────────────────────────────────────────────────────────────────────────
  // LIFECYCLE
  // ────────────────────────────────────────────────────────────────────────────
  onMounted(async () => {
    // a) initial config + start timer
    startTimer()
    try {
      const cfg = await client.fetchConfig()
      if (cfg.background) backgroundPath.value = cfg.background
      if (typeof cfg.fps === 'number' && cfg.fps > 0) {
        fps.value = cfg.fps + 1
      }
    } catch (e) {
      console.error('[Module1] fetchConfig error', e)
    }

    // b) WebSocket push + timerControl handling
    client.onMessage((msg: any) => {
      if (msg.action === 'get_buffer') {
        const buf = msg.buffer as BufferPayload
        x.value = buf.x ?? x.value
        y.value = buf.y ?? y.value
        diamPx.value = buf.diameter ?? diamPx.value

        // handle timerControl commands
        if (buf.timerControl === 'pause') pauseTimer()
        if (buf.timerControl === 'resume') resumeTimer()
        if (buf.timerControl === 'reset') resetTimer()
      }
    })

    // c) HTTP polling fallback
    try {
      const buf0 = await client.getBuffer()
      x.value = buf0.x ?? x.value
      y.value = buf0.y ?? y.value
      diamPx.value = buf0.diameter ?? diamPx.value
    } catch {}

    pollTimer = window.setInterval(async () => {
      try {
        const buf = await client.getBuffer()
        x.value = buf.x ?? x.value
        y.value = buf.y ?? y.value
        diamPx.value = buf.diameter ?? diamPx.value
      } catch {}
    }, Math.round(1000 / fps.value))

    // d) réponse "bonne"
    watch([x, y], ([newX, newY]) => {
      const dx = newX - goodResponsePosition.x
      const dy = newY - goodResponsePosition.y
      const distance = Math.hypot(dx, dy)
      const now = performance.now() / 1000
      if (distance <= goodResponseZoneSize) {
        if (!inZone.value) {
          inZone.value = true
          entryTime = now
          responseAlreadyValidated = false
        } else if (!responseAlreadyValidated && entryTime !== null) {
          if (now - entryTime >= goodResponseStayTime) {
            responseAlreadyValidated = true
          }
        }
      } else {
        inZone.value = false
        entryTime = null
        responseAlreadyValidated = false
      }
    })
  })

  onBeforeUnmount(() => {
    if (pollTimer) clearInterval(pollTimer)
    if (timerInterval) clearInterval(timerInterval)
  })

  return {
    backgroundPath,
    filterStyle,
    x,
    y,
    diamPx,
    fps,
    inZone,
    entryTime,
    responseAlreadyValidated,
    timerColor,
    timerText,
    pauseTimer,
    resumeTimer,
    resetTimer
  }
}
