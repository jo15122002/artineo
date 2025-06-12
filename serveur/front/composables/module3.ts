// File: serveur/front/composables/module3.ts
import { computed, onBeforeUnmount, onMounted, ref, type Ref } from 'vue'
import { useArtineo } from './useArtineo'

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

  const timerText = ref<string>('1:00')

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

  function updateFromBuffer(buf: any) {
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

      if (typeof buf.timer === 'string') {
        timerText.value = buf.timer
      }

      setTimeout(() => {
        states.value        = states.value.map(s => s === 'wrong' ? 'default' : s)
        pressedStates.value = states.value.map(s => s === 'correct')
      }, 2000)
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
    }, 1000)
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
    timerText
  }
}
