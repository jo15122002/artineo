// File: serveur/front/composables/module3.ts
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
  const hr = r.toString(16).padStart(2, '0')
  const hg = g.toString(16).padStart(2, '0')
  const hb = b.toString(16).padStart(2, '0')
  return `#${hr}${hg}${hb}`
}
function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t
}

export default function useModule3(
  playerRef: Ref<InstanceType<typeof import('~/components/ArtyPlayer.vue').default> | null>
) {
  // Guard SSR : rien à faire côté serveur
  if (!process.client) {
    const backgroundSet  = ref<number>(1)
    const blobTexts      = ref<string[]>(['Lieu','Couleur','Émotion'])
    const states         = ref<Array<'default'|'correct'|'wrong'>>(['default','default','default'])
    const stateClasses   = computed(() => states.value.map(s => `state-${s}`))
    const pressedStates  = ref<boolean[]>([false,false,false])
    return {
      backgroundSet,
      blobTexts,
      stateClasses,
      pressedStates
    }
  }

  const moduleId = 3
  const client   = useArtineo(moduleId)

  const backgroundSet = ref<number>(1)
  const blobTexts     = ref<string[]>(['Lieu','Couleur','Émotion'])
  const states        = ref<Array<'default'|'correct'|'wrong'>>(['default','default','default'])
  const stateClasses  = computed(() => states.value.map(s => `state-${s}`))
  const pressedStates = ref<boolean[]>([false,false,false])
  let prevPressed     = false

  const TIMER_DURATION = 60; // duree en secondes
  const timerSeconds = ref<number>(TIMER_DURATION)
  let timerInterval: number | undefined = undefined

  const pluralMap: Record<string,string> = {
    lieu:    'lieux',
    couleur: 'couleurs',
    emotion: 'emotions'
  }

  function startTimer() {
    // réinitialise la valeur et stoppe un éventuel timer en cours
    if (timerInterval) {
      clearInterval(timerInterval)
    }
    timerSeconds.value = TIMER_DURATION
    // décrémente chaque seconde
    timerInterval = window.setInterval(() => {
      // on décompte et on s'assure de ne pas passer sous 0
      timerSeconds.value = Math.max(timerSeconds.value - 1, 0)
      if (timerSeconds.value === 0 && timerInterval) {
        clearInterval(timerInterval)
      }
    }, 1000)
  }

  function stopTimer() {
    if (timerInterval) {
      clearInterval(timerInterval)
      timerInterval = undefined
    }
    timerSeconds.value = TIMER_DURATION // réinitialise la valeur
  }

  // computed pour formater en M:SS
  const timerText = computed(() => {
    const m = Math.floor(timerSeconds.value / 60);
    const s = timerSeconds.value % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  });

  const colorStops = [
    { p: 1.0, color: '#2626FF' },
    { p: 0.6, color: '#FA81C3' },
    { p: 0.3, color: '#FA4923' }
  ] as const

  const timerColor = computed(() => {
    // ratio entre 0 et 1
    const pct = timerSeconds.value / TIMER_DURATION
    // on parcourt chaque segment [i]→[i+1]
    for (let i = 0; i < colorStops.length - 1; i++) {
      const { p: p0, color: c0 } = colorStops[i]
      const { p: p1, color: c1 } = colorStops[i+1]
      if (pct <= p0 && pct >= p1) {
        // t = 0 à p0  → couleur c0
        // t = 1 à p1  → couleur c1
        const t = (p0 - pct) / (p0 - p1)
        const rgb0 = hexToRgb(c0)
        const rgb1 = hexToRgb(c1)
        const r = Math.round(lerp(rgb0.r, rgb1.r, t))
        const g = Math.round(lerp(rgb0.g, rgb1.g, t))
        const b = Math.round(lerp(rgb0.b, rgb1.b, t))
        return rgbToHex(r, g, b)
      }
    }
    // fallback
    return colorStops[colorStops.length - 1].color
  })

  function lookupLabel(map: Record<string,string>, code: string): string {
    const inv: Record<string,string> = {}
    for (const [label, uid] of Object.entries(map)) {
      inv[uid.toLowerCase()] = label
    }
    return inv[code.toLowerCase()] || 'Inconnu'
  }

  function updateFromBuffer(buf: any) {
    console.log('[useModule3] updateFromBuffer', buf)
    if (buf.current_set && buf.current_set !== backgroundSet.value) {
      backgroundSet.value  = buf.current_set
      states.value         = ['default','default','default']
      pressedStates.value  = [false,false,false]
      prevPressed          = false
    }

    const texts   = ['Lieu','Couleur','Émotion']
    const colors  = ['#FFA500','#FFA500','#FFA500']
    const keys    = ['lieu','couleur','emotion'] as const
    const uidKeys = ['uid1','uid2','uid3']      as const
    const setIdx  = (backgroundSet.value || 1) - 1
    const answers = (client as any).answers || []

    keys.forEach((key,i) => {
      const cat        = pluralMap[key]
      const assignMap  = (client as any).assignments?.[cat] || {}
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

    if (typeof buf.timer === 'string') {
        console.log('[useModule3] timer received:', buf.timer)
        timerText.value = buf.timer
    }

    prevPressed = !!buf.button_pressed
  }

  async function fetchBufferHttp(): Promise<any> {
    const res = await fetch(`${useRuntimeConfig().public.apiUrl}/buffer?module=${moduleId}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const js = await res.json() as { buffer: any }
    return js.buffer
  }

  let poll: ReturnType<typeof setInterval>
  onMounted(async () => {
    try {
      const cfg = await client.fetchConfig()
      ;(client as any).assignments = cfg.assignments || {}
      ;(client as any).answers     = cfg.answers     || []
    } catch (e) {
      console.warn('[useModule3] fetchConfig error', e)
    }

    client.onMessage((msg: any) => {
      if (msg.action === 'get_buffer') {
        updateFromBuffer(msg.buffer as any)
      }
    })

    try {
      updateFromBuffer(await fetchBufferHttp())
    } catch (e) {
      console.warn('[useModule3] fetchBufferHttp initial error', e)
    }
    poll = setInterval(async () => {
      try {
        updateFromBuffer(await fetchBufferHttp())
      } catch {
        // ignore
      }
    }, 500)
  })

  onBeforeUnmount(() => {
    clearInterval(poll)
  })

  const backgroundUrl = computed(
    () => `${useRuntimeConfig().public.apiUrl}/getAsset?module=3&path=tableau${backgroundSet.value}.png`
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
    stopTimer
  }
}
