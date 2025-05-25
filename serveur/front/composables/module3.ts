import { useNuxtApp } from '#app'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { BufferPayload } from '~/utils/ArtineoClient'

export default function useModule3() {
  // Stub pour SSR : on initialise aux mêmes valeurs qu’en client
  if (!process.client) {
    const backgroundSet = ref<number>(1)
    const blobTexts     = ref<string[]>(['Aucun', 'Aucun', 'Aucun'])
    const blobColors    = ref<string[]>(['#FFA500', '#FFA500', '#FFA500'])
    return {
      backgroundSet,
      blobTexts,
      blobColors
    }
  }

  const moduleId = 3
  const { $artineo } = useNuxtApp()
  if (typeof $artineo !== 'function') {
    throw new Error('Plugin $artineo non injecté — vérifie plugins/artineo.ts')
  }
  const client = $artineo(moduleId)

  // États réactifs
  const assignments   = ref<Record<string, Record<string, string>>>({})
  const answers       = ref<Array<Record<string, string>>>([])
  const backgroundSet = ref<number>(1)
  const blobTexts     = ref<string[]>(['Aucun', 'Aucun', 'Aucun'])
  const blobColors    = ref<string[]>(['#FFA500', '#FFA500', '#FFA500'])

  let pollTimer: number

  // Pour corriger le pluriel de chaque catégorie
  const pluralMap: Record<string,string> = {
    lieu:    'lieux',
    couleur: 'couleurs',
    emotion: 'emotions'
  }

  // Inverse un mapping label→uid en uid→label (casse ignorée)
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

  // Applique le buffer aux blobs
  function updateFromBuffer(buf: BufferPayload) {
    console.log('[Module3] updateFromBuffer', buf)

    // 1) mise à jour du set si changé
    if (buf.current_set && buf.current_set !== backgroundSet.value) {
      backgroundSet.value = buf.current_set
      console.log('[Module3] backgroundSet mis à jour →', backgroundSet.value)
    }

    // 2) valeurs par défaut
    const texts  = ['Aucun', 'Aucun', 'Aucun']
    const colors = ['#FFA500', '#FFA500', '#FFA500']

    // 3) pour chaque catégorie, on cherche dans uid1/2/3
    const keys    = ['lieu','couleur','emotion'] as const
    const uidKeys = ['uid1','uid2','uid3'] as const
    const setIdx  = (backgroundSet.value || 1) - 1

    keys.forEach((key, i) => {
      const cat     = pluralMap[key]         // ex. 'lieux'
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

    console.log('[Module3] blobTexts →', blobTexts.value)
    console.log('[Module3] blobColors →', blobColors.value)
  }

  onMounted(async () => {
    console.log('[Module3] onMounted: début fetchConfig')
    // a) fetchConfig
    try {
      const cfg = await client.fetchConfig()
      console.log('[Module3] fetchConfig réussi →', cfg)
      assignments.value = cfg.assignments || {}
      answers.value     = cfg.answers     || []
      console.log('[Module3] assignments & answers initialisés')
    } catch (e) {
      console.error('[Module3] fetchConfig error', e)
    }

    // b) réception WS
    client.onMessage(msg => {
      if (msg.action === 'get_buffer') {
        console.log('[Module3] WS reçu get_buffer →', msg.buffer)
        updateFromBuffer(msg.buffer as BufferPayload)
      }
    })

    // c) fallback HTTP + polling
    console.log('[Module3] récupération initiale du buffer via HTTP')
    try {
      const buf0 = await client.getBuffer()
      console.log('[Module3] getBuffer initial →', buf0)
      updateFromBuffer(buf0)
    } catch (e) {
      console.warn('[Module3] getBuffer initial error', e)
    }

    pollTimer = window.setInterval(async () => {
      console.log('[Module3] polling getBuffer...')
      try {
        const buf = await client.getBuffer()
        console.log('[Module3] getBuffer polling →', buf)
        updateFromBuffer(buf)
      } catch (e) {
        console.warn('[Module3] getBuffer polling error', e)
      }
    }, 1000)
  })

  onBeforeUnmount(() => {
    clearInterval(pollTimer)
    client.close()
    console.log('[Module3] onBeforeUnmount: polling arrêté, client fermé')
  })

  return {
    backgroundSet,
    blobTexts,
    blobColors
  }
}
