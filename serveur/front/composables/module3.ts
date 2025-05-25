import { useNuxtApp, useRuntimeConfig } from '#app'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { BufferPayload } from '~/utils/ArtineoClient'

export default function useModule3() {
  // Stub SSR
  if (!process.client) {
    const backgroundSet = ref<number>(1)
    const blobTexts    = ref<string[]>(['Aucun', 'Aucun', 'Aucun'])
    const states       = ref<('default')[]>(['default','default','default'])
    const stateClasses = computed(() => states.value.map(s => `state-${s}`))
    return { backgroundSet, blobTexts, states, stateClasses }
  }

  const moduleId = 3
  const { $artineo } = useNuxtApp()
  const { public: { apiUrl } } = useRuntimeConfig()
  const client = $artineo(moduleId)

  // Reactive state
  const backgroundSet = ref<number>(1)
  const blobTexts     = ref<string[]>(['Aucun', 'Aucun', 'Aucun'])
  const blobColors    = ref<string[]>(['#FFA500', '#FFA500', '#FFA500'])
  const states        = ref<Array<'default'|'correct'|'wrong'>>(['default','default','default'])
  const stateClasses  = computed(() => states.value.map(s => `state-${s}`))

  const httpBufferUrl = `${apiUrl}/buffer?module=${moduleId}`

  // Pluriels pour lookup
  const pluralMap: Record<string,string> = {
    lieu:    'lieux',
    couleur: 'couleurs',
    emotion: 'emotions'
  }

  // Inverse label→uid en uid→label
  function lookupLabel(map: Record<string,string>, code: string): string {
    const inv: Record<string,string> = {}
    for (const [label, uid] of Object.entries(map)) {
      inv[uid.toLowerCase()] = label
    }
    return inv[code.toLowerCase()] || 'Inconnu'
  }

  // Applique le buffer reçu via WS ou HTTP
  function updateFromBuffer(buf: BufferPayload) {
    // Changement de set ?
    if (buf.current_set && buf.current_set !== backgroundSet.value) {
      backgroundSet.value = buf.current_set
    }

    // Defaults
    const texts  = ['Aucun','Aucun','Aucun']
    const colors = ['#FFA500','#FFA500','#FFA500']

    const keys    = ['lieu','couleur','emotion'] as const
    const uidKeys = ['uid1','uid2','uid3'] as const
    const setIdx  = (backgroundSet.value || 1) - 1

    // Remplissage des textes & couleurs
    keys.forEach((key,i) => {
      const cat     = pluralMap[key]
      const map     = (client as any).assignments?.[cat] || {}
      const correct = (client as any).answers?.[setIdx]?.[key]?.toLowerCase()
      for (const uk of uidKeys) {
        const code = buf[uk as keyof BufferPayload]
        if (typeof code === 'string') {
          const label = lookupLabel(map, code)
          if (label !== 'Inconnu') {
            texts[i]  = label
            colors[i] = code.toLowerCase() === correct
              ? '#00FF00'
              : '#FF0000'
            break
          }
        }
      }
    })

    blobTexts.value  = texts
    blobColors.value = colors

    // États visuels
    if (buf.button_pressed) {
      // Au clic : verts/rouges
      states.value = colors.map(c => c === '#00FF00' ? 'correct' : c === '#FF0000' ? 'wrong' : 'default')
      // Après 2s : on repasse les "wrong" en default
      setTimeout(() => {
        states.value = states.value.map(s => s === 'wrong' ? 'default' : s)
      }, 2000)
    } else {
      // Avant validation : tous en default
      states.value = ['default','default','default']
    }
  }

  // Fetch HTTP en fallback
  async function fetchBufferHttp(): Promise<BufferPayload> {
    const res = await fetch(httpBufferUrl)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const json = await res.json() as { buffer: BufferPayload }
    return json.buffer
  }

  onMounted(async () => {
    // 1) Config initiale
    try {
      const cfg = await client.fetchConfig()
      // Stockez assignments & answers localement pour lookupLabel
      ;(client as any).assignments = cfg.assignments || {}
      ;(client as any).answers     = cfg.answers     || []
    } catch {}

    // 2) WS receive
    client.onMessage((msg: any) => {
      if (msg.action === 'get_buffer') {
        updateFromBuffer(msg.buffer as BufferPayload)
      }
    })

    // 3) Fallback initial HTTP
    try {
      const buf0 = await fetchBufferHttp()
      updateFromBuffer(buf0)
    } catch {}

    // 4) Polling HTTP toutes les secondes
    const poll = setInterval(async () => {
      try {
        const buf = await fetchBufferHttp()
        updateFromBuffer(buf)
      } catch {}
    }, 1000)

    onBeforeUnmount(() => {
      clearInterval(poll)
      client.close()
    })
  })

  return {
    backgroundSet,
    blobTexts,
    blobColors,
    states,
    stateClasses
  }
}