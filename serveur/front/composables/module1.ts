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
      timerText: stub,
      pauseTimer: stub,
      resumeTimer: stub,
      resetTimer: stub
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

  // ────────────────────────────────────────────────────────────────────────────
  // Validation “bonne réponse”
  // ────────────────────────────────────────────────────────────────────────────
  const goodResponsePosition = { x: 160, y: 120 }
  // tolérance en px (horizontale et verticale)
  const positionTolerance = 30
  // durée minimale à rester dans la zone (s)
  const stayTime = 2.0

  const inZone = ref(false)
  let entryTime: number | null = null
  let responseAlreadyValidated = false

  // CSS filter pour feed-back visuel
  const filterStyle = computed(() => {
    const dx = x.value - goodResponsePosition.x
    const dy = y.value - goodResponsePosition.y
    let hueVal = (dx / goodResponsePosition.x) * 180
    hueVal = Math.max(-180, Math.min(180, hueVal))
    const refDiam = positionTolerance
    let satVal = 100 + ((diamPx.value - refDiam) / refDiam) * 100
    satVal = Math.max(0, Math.min(200, satVal))
    let brightVal = 100 - (dy / goodResponsePosition.y) * 50
    brightVal = Math.max(50, Math.min(150, brightVal))
    return `hue-rotate(${hueVal.toFixed(1)}deg)
            saturate(${satVal.toFixed(0)}%)
            brightness(${brightVal.toFixed(0)}%)`
  })

  // ────────────────────────────────────────────────────────────────────────────
  // Timer (inchangé)
  // ────────────────────────────────────────────────────────────────────────────
  const TIMER_DURATION = 60
  const timerSeconds = ref<number>(TIMER_DURATION)
  let timerInterval: number | undefined

  function startTimer() {
    console.log('[Module1] Timer start')
    if (timerInterval) clearInterval(timerInterval)
    timerSeconds.value = TIMER_DURATION
    timerInterval = window.setInterval(() => {
      timerSeconds.value = Math.max(timerSeconds.value - 1, 0)
      if (timerSeconds.value === 0 && timerInterval) clearInterval(timerInterval)
    }, 1000)
  }
  function pauseTimer() {
    console.log('[Module1] Timer pause at', timerSeconds.value)
    if (timerInterval) {
      clearInterval(timerInterval)
      timerInterval = undefined
    }
  }
  function resumeTimer() {
    console.log('[Module1] Timer resume at', timerSeconds.value)
    if (!timerInterval && timerSeconds.value > 0) {
      timerInterval = window.setInterval(() => {
        timerSeconds.value = Math.max(timerSeconds.value - 1, 0)
        if (timerSeconds.value === 0 && timerInterval) clearInterval(timerInterval)
      }, 1000)
    }
  }
  function resetTimer() {
    console.log('[Module1] Timer reset')
    pauseTimer()
    timerSeconds.value = TIMER_DURATION
  }

  function hexToRgb(hex: string) {
    const h = hex.replace('#','')
    const bigint = parseInt(h,16)
    return {
      r: (bigint>>16)&0xff,
      g: (bigint>>8)&0xff,
      b: bigint&0xff
    }
  }
  function rgbToHex(r:number,g:number,b:number) {
    const to2 = (x:number)=>x.toString(16).padStart(2,'0')
    return `#${to2(r)}${to2(g)}${to2(b)}`
  }
  function lerp(a:number,b:number,t:number){ return a + (b-a)*t }

  const colorStops = [
    { p:1.0, color:'#2626FF' },
    { p:0.6, color:'#FA81C3' },
    { p:0.3, color:'#FA4923' }
  ] as const

  const timerColor = computed(() => {
    const pct = timerSeconds.value / TIMER_DURATION
    for (let i=0; i<colorStops.length-1; i++) {
      const { p:p0, color:c0 } = colorStops[i]
      const { p:p1, color:c1 } = colorStops[i+1]
      if (pct <= p0 && pct >= p1) {
        const t = (p0 - pct)/(p0 - p1)
        const a = hexToRgb(c0), b = hexToRgb(c1)
        return rgbToHex(
          Math.round(lerp(a.r,b.r,t)),
          Math.round(lerp(a.g,b.g,t)),
          Math.round(lerp(a.b,b.b,t))
        )
      }
    }
    return colorStops[colorStops.length-1].color
  })

  const timerText = computed(() => {
    const m = Math.floor(timerSeconds.value/60)
    const s = timerSeconds.value%60
    return `${m}:${String(s).padStart(2,'0')}`
  })

  // ────────────────────────────────────────────────────────────────────────────
  // LIFECYCLE
  // ────────────────────────────────────────────────────────────────────────────
  const fps = ref(10)
  let pollTimer: number | undefined

  onMounted(async () => {
    console.log('[Module1] Mounted, starting timer & WS')
    startTimer()
    try {
      const cfg = await client.fetchConfig()
      console.log('[Module1] fetchConfig →', cfg)
      if (cfg.background) backgroundPath.value = cfg.background
      if (typeof cfg.fps === 'number' && cfg.fps > 0) {
        fps.value = cfg.fps + 1
      }
    } catch (e) {
      console.error('[Module1] fetchConfig error', e)
    }

    // WS push + contrôle timer
    client.onMessage((msg:any) => {
      // console.log('[Module1] WS message →', msg)
      if (msg.action === 'get_buffer') {
        const buf = msg.buffer as BufferPayload
        x.value      = buf.x      ?? x.value
        y.value      = buf.y      ?? y.value
        diamPx.value = buf.diameter ?? diamPx.value
        if (buf.timerControl==='pause')  pauseTimer()
        if (buf.timerControl==='resume') resumeTimer()
        if (buf.timerControl==='reset')  resetTimer()
      }
    })

    // fallback HTTP
    try {
      const buf0 = await client.getBuffer()
      console.log('[Module1] initial HTTP buffer →', buf0)
      x.value      = buf0.x      ?? x.value
      y.value      = buf0.y      ?? y.value
      diamPx.value = buf0.diameter ?? diamPx.value
    } catch (e) {
      console.warn('[Module1] initial HTTP error', e)
    }

    pollTimer = window.setInterval(async () => {
      try {
        const buf = await client.getBuffer()
        x.value      = buf.x      ?? x.value
        y.value      = buf.y      ?? y.value
        diamPx.value = buf.diameter ?? diamPx.value
      } catch {}
    }, Math.round(1000/fps.value))

    // === validation “bonne réponse” ===
    watch([x,y], ([newX,newY]) => {
      const dx = newX - goodResponsePosition.x
      const dy = newY - goodResponsePosition.y
      const now = performance.now()/1000
      // console.log(`[Module1] Checking zone: dx=${dx.toFixed(1)}, dy=${dy.toFixed(1)}, time=${now.toFixed(3)}`)
      if (Math.abs(dx) <= positionTolerance && Math.abs(dy) <= positionTolerance) {
        if (!inZone.value) {
          inZone.value = true
          entryTime = now
          responseAlreadyValidated = false
          console.log(`[Module1] Entered zone at ${now.toFixed(3)}s`)
        } else if (!responseAlreadyValidated && entryTime !== null) {
          if (now - entryTime >= stayTime) {
            responseAlreadyValidated = true
            console.log(`[Module1] VALIDATED at ${now.toFixed(3)}s (stayed ${ (now-entryTime).toFixed(3) }s)`)
          }
        }
      } else {
        if (inZone.value) {
          console.log(`[Module1] Exited zone at ${now.toFixed(3)}s`)
        }
        inZone.value = false
        entryTime = null
        responseAlreadyValidated = false
      }
    })
  })

  onBeforeUnmount(() => {
    console.log('[Module1] Unmount, clearing timers')
    if (pollTimer)    clearInterval(pollTimer)
    if (timerInterval) clearInterval(timerInterval)
  })

  return {
    backgroundPath,
    filterStyle,
    x, y, diamPx,
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
