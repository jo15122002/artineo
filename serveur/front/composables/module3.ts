// File: serveur/front/composables/module3.ts
import { useRuntimeConfig } from '#app'
import { computed, onBeforeUnmount, onMounted, ref, type Ref } from 'vue'
import { useArtineo } from './useArtineo'

function hexToRgb(hex: string) {
  const h = hex.replace('#','')
  const bigint = parseInt(h, 16)
  return {
    r: (bigint >> 16) & 0xFF,
    g: (bigint >> 8)  & 0xFF,
    b:  bigint        & 0xFF,
  }
}
function rgbToHex(r: number, g: number, b: number) {
  const to2 = (x: number) => x.toString(16).padStart(2, '0')
  return `#${to2(r)}${to2(g)}${to2(b)}`
}
function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t
}

export default function useModule3(
  playerRef: Ref<InstanceType<typeof import('~/components/ArtyPlayer.vue').default> | null>
) {
  // SSR stub
  if (!process.client) {
    const stubNum = ref(1)
    const stubArr = ref<string[]>(['Lieu','Couleur','Émotion'])
    const stubStates = ref<Array<'default'|'correct'|'wrong'>>(['default','default','default'])
    const stubBoolArr = ref<boolean[]>([false,false,false])
    const stubText = ref('1:00')
    const stubColor = ref('#2626FF')
    const stubUrl = computed(() => '')
    const noop = () => {}
    return {
      backgroundSet: stubNum,
      blobTexts: stubArr,
      stateClasses: computed(() => stubStates.value.map(s => `state-${s}`)),
      pressedStates: stubBoolArr,
      backgroundUrl: stubUrl,
      timerText: stubText,
      timerColor: stubColor,
      startTimer: noop,
      stopTimer: noop,
      pauseTimer: noop,
      resumeTimer: noop,
      resetTimer: noop
    }
  }

  const moduleId = 3
  const client   = useArtineo(moduleId)
  const { public: { apiUrl } } = useRuntimeConfig()

  // reactive state
  const backgroundSet = ref<number>(1)
  const blobTexts     = ref<string[]>(['Lieu','Couleur','Émotion'])
  const states        = ref<Array<'default'|'correct'|'wrong'>>(['default','default','default'])
  const stateClasses  = computed(() => states.value.map(s => `state-${s}`))
  const pressedStates = ref<boolean[]>([false,false,false])
  let prevPressed     = false

  // timer logic
  const TIMER_DURATION = 60
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

  const timerText = computed(() => {
    const m = Math.floor(timerSeconds.value / 60)
    const s = timerSeconds.value % 60
    return `${m}:${String(s).padStart(2,'0')}`
  })

  const colorStops = [
    { p: 1.0, color: '#2626FF' },
    { p: 0.6, color: '#FA81C3' },
    { p: 0.3, color: '#FA4923' }
  ] as const
  const timerColor = computed(() => {
    const pct = timerSeconds.value / TIMER_DURATION
    for (let i = 0; i < colorStops.length - 1; i++) {
      const { p: p0, color: c0 } = colorStops[i]
      const { p: p1, color: c1 } = colorStops[i+1]
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

  // localization helpers
  const pluralMap: Record<string,string> = {
    lieu:    'lieux',
    couleur: 'couleurs',
    emotion: 'emotions'
  }
  function lookupLabel(map: Record<string,string>, code: string): string {
    const inv: Record<string,string> = {}
    for (const [label, uid] of Object.entries(map)) {
      inv[uid.toLowerCase()] = label
    }
    return inv[code.toLowerCase()] || 'Inconnu'
  }

  // buffer handling
  function updateFromBuffer(buf: any) {
    if (buf.current_set && buf.current_set !== backgroundSet.value) {
      backgroundSet.value  = buf.current_set
      states.value         = ['default','default','default']
      pressedStates.value  = [false,false,false]
      prevPressed          = false
    }
    const texts  = ['Lieu','Couleur','Émotion']
    const colors = ['#FFA500','#FFA500','#FFA500']
    const keys   = ['lieu','couleur','emotion'] as const
    const uidKeys= ['uid1','uid2','uid3']      as const
    const setIdx = backgroundSet.value - 1
    const answers = (client as any).answers || []
    const assignments = (client as any).assignments || {}

    keys.forEach((key,i) => {
      const cat        = pluralMap[key]
      const assignMap  = assignments[cat] || {}
      const correctUid = answers[setIdx]?.[key]?.toLowerCase()
      for (const uk of uidKeys) {
        const code = buf[uk as keyof typeof buf]
        if (typeof code === 'string') {
          const lbl = lookupLabel(assignMap, code)
          if (lbl !== 'Inconnu') {
            texts[i]  = lbl
            colors[i] = code.toLowerCase() === correctUid ? '#00FF00' : '#FF0000'
            break
          }
        }
      }
    })
    blobTexts.value = texts

    if (buf.button_pressed && !prevPressed) {
      states.value = colors.map(c =>
        c === '#00FF00' ? 'correct'
        : c === '#FF0000' ? 'wrong'
        : 'default'
      )
      pressedStates.value = [true, true, true]
      setTimeout(() => {
        states.value        = states.value.map(s => s === 'wrong' ? 'default' : s)
        pressedStates.value = states.value.map(s => s === 'correct')
      }, 2000)
    }

    prevPressed = !!buf.button_pressed
  }

  async function fetchBufferHttp(): Promise<any> {
    const res = await fetch(`${apiUrl}/buffer?module=${moduleId}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return (await res.json() as { buffer: any }).buffer
  }

  let poll: ReturnType<typeof setInterval>

  onMounted(async () => {
    // fetch config
    try {
      const cfg = await client.fetchConfig()
      ;(client as any).assignments = cfg.assignments || {}
      ;(client as any).answers     = cfg.answers     || []
    } catch (e) {
      console.warn('[useModule3] fetchConfig error', e)
    }

    // WebSocket push + timerControl
    client.onMessage((msg: any) => {
      if (msg.action === 'get_buffer') {
        updateFromBuffer(msg.buffer)
        const ctl = (msg.buffer as any).timerControl
        if (ctl === 'pause')   pauseTimer()
        if (ctl === 'resume')  resumeTimer()
        if (ctl === 'reset')   resetTimer()
      }
    })

    // initial HTTP + polling
    try {
      updateFromBuffer(await fetchBufferHttp())
    } catch (e) {
      console.warn('[useModule3] initial HTTP error', e)
    }
    poll = setInterval(async () => {
      try {
        const buf = await fetchBufferHttp()
        updateFromBuffer(buf)
        const ctl = (buf as any).timerControl
        if (ctl === 'pause')   pauseTimer()
        if (ctl === 'resume')  resumeTimer()
        if (ctl === 'reset')   resetTimer()
      } catch {}
    }, 500)
  })

  onBeforeUnmount(() => {
    clearInterval(poll)
    if (timerInterval) clearInterval(timerInterval)
  })

  const backgroundUrl = computed(
    () => `${apiUrl}/getAsset?module=3&path=tableau${backgroundSet.value}.png`
  )

  return {
    backgroundSet,
    blobTexts,
    stateClasses,
    pressedStates,
    backgroundUrl,
    timerText,
    timerColor,
    startTimer,
    pauseTimer,
    resumeTimer,
    resetTimer
  }
}
