// serveur/front/composables/module3.ts
import { useNuxtApp, useRuntimeConfig } from '#app'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { BufferPayload } from '~/utils/ArtineoClient'

export default function useModule3() {
  // Stub pour SSR
  if (!process.client) {
    const backgroundSet = ref<number>(1)
    const blobTexts     = ref<string[]>(['Aucun', 'Aucun', 'Aucun'])
    const blobColors    = ref<string[]>(['#FFA500', '#FFA500', '#FFA500'])
    return { backgroundSet, blobTexts, blobColors }
  }

  const moduleId = 3
  const { $artineo } = useNuxtApp()
  const { public: { apiUrl } } = useRuntimeConfig()
  if (typeof $artineo !== 'function') {
    throw new Error('Plugin $artineo non injecté — vérifie plugins/artineo.ts')
  }
  const client = $artineo(moduleId)

  // URL HTTP pour fallback
  const httpBufferUrl = `${apiUrl}/buffer?module=${moduleId}`

  // États réactifs
  const assignments   = ref<Record<string, Record<string, string>>>({})
  const answers       = ref<Array<Record<string, string>>>([])
  const backgroundSet = ref<number>(1)
  const blobTexts     = ref<string[]>(['Aucun', 'Aucun', 'Aucun'])
  const blobColors    = ref<string[]>(['#FFA500', '#FFA500', '#FFA500'])

  let pollTimer: number

  // Pour corriger le pluriel
  const pluralMap: Record<string,string> = {
    lieu:    'lieux',
    couleur: 'couleurs',
    emotion: 'emotions'
  }

  // Inverse label→uid en uid→label
  function lookupLabel(
    map: Record<string, string>,
    code: string
  ): string {
    const inv: Record<string, string> = {}
    for (const [label, uid] of Object.entries(map)) {
      inv[uid.toLowerCase()] = label
    }
    return inv[code.toLowerCase()] || 'Inconnu'
  }

  // Applique un buffer reçu
  function updateFromBuffer(buf: BufferPayload) {
    console.log('[Module3] updateFromBuffer', buf)

    // changement de set ?
    if (buf.current_set && buf.current_set !== backgroundSet.value) {
      backgroundSet.value = buf.current_set
      console.log('[Module3] backgroundSet →', buf.current_set)
    }

    // defaults
    const texts  = ['Aucun', 'Aucun', 'Aucun']
    const colors = ['#FFA500', '#FFA500', '#FFA500']

    const keys    = ['lieu','couleur','emotion'] as const
    const uidKeys = ['uid1','uid2','uid3'] as const
    const setIdx  = (backgroundSet.value || 1) - 1

    keys.forEach((key, i) => {
      const cat     = pluralMap[key]
      const map     = assignments.value[cat] || {}
      const correct = answers.value[setIdx]?.[key]?.toLowerCase()

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

    console.log('[Module3] blobTexts →', texts)
    console.log('[Module3] blobColors →', colors)
  }

  // Fetch HTTP simple
  async function fetchBufferHttp(): Promise<BufferPayload> {
    console.log('[Module3] fetchBufferHttp → GET', httpBufferUrl)
    const res = await fetch(httpBufferUrl)
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }
    const json = await res.json() as { buffer: BufferPayload }
    console.log('[Module3] fetchBufferHttp reçu →', json.buffer)
    return json.buffer
  }

  onMounted(async () => {
    // 1) config HTTP
    console.log('[Module3] onMounted: début fetchConfig')
    try {
      const cfg = await client.fetchConfig()
      console.log('[Module3] fetchConfig réussi →', cfg)
      assignments.value = cfg.assignments || {}
      answers.value     = cfg.answers     || []
      console.log('[Module3] assignments & answers initialisés')
    } catch (e) {
      console.error('[Module3] fetchConfig error', e)
    }

    // 2) réception WS
    client.onMessage(msg => {
      if (msg.action === 'get_buffer') {
        console.log('[Module3] WS get_buffer →', msg.buffer)
        updateFromBuffer(msg.buffer as BufferPayload)
      }
    })

    // 3) fallback initial via HTTP
    console.log('[Module3] récupération initiale du buffer via HTTP')
    try {
      const buf0 = await fetchBufferHttp()
      updateFromBuffer(buf0)
    } catch (e) {
      console.warn('[Module3] fetchBufferHttp initial error', e)
    }

    // 4) polling toutes les secondes via HTTP
    pollTimer = window.setInterval(async () => {
      console.log('[Module3] polling fetchBufferHttp...')
      try {
        const buf = await fetchBufferHttp()
        updateFromBuffer(buf)
      } catch (e) {
        console.warn('[Module3] fetchBufferHttp polling error', e)
      }
    }, 1000)
  })

  onBeforeUnmount(() => {
    clearInterval(pollTimer)
    client.close()
    console.log('[Module3] onBeforeUnmount: polling stoppé, client fermé')
  })

  return {
    backgroundSet,
    blobTexts,
    blobColors
  }
}
