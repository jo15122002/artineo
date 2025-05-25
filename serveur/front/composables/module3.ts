// front/composables/module3.ts
import { useNuxtApp } from '#app'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { BufferPayload } from '~/utils/ArtineoClient'

export default function useModule3() {
  // Stub pour SSR
  if (!process.client) {
    const empty = ref<any>(null)
    return {
      backgroundSet: empty,
      blobTexts:     empty,
      blobColors:    empty
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
  const blobTexts     = ref<string[]>(['', '', ''])
  const blobColors    = ref<string[]>(['', '', ''])

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
    // 1) mise à jour du tableau
    if (buf.current_set && buf.current_set !== backgroundSet.value) {
      backgroundSet.value = buf.current_set
    }

    // 2) valeurs par défaut
    const texts  = ['Aucun', 'Aucun', 'Aucun']
    const colors = ['#FFA500', '#FFA500', '#FFA500']

    // 3) pour chaque catégorie, on cherche dans uid1/2/3
    const keys   = ['lieu','couleur','emotion'] as const
    const uidKeys= ['uid1','uid2','uid3'] as const
    const setIdx = (backgroundSet.value || 1) - 1

    keys.forEach((key, i) => {
      const cat    = pluralMap[key]         // ex. 'lieux'
      const map    = assignments.value[cat] || {}
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
  }

  onMounted(async () => {
    // a) fetchConfig
    try {
      const cfg = await client.fetchConfig()
      assignments.value   = cfg.assignments || {}
      answers.value       = cfg.answers     || []
    } catch (e) {
      console.error('[Module3] fetchConfig error', e)
    }

    // b) réception WS
    client.onMessage(msg => {
      if (msg.action === 'get_buffer') {
        updateFromBuffer(msg.buffer as BufferPayload)
      }
    })

    // c) fallback HTTP + polling
    try {
      const buf0 = await client.getBuffer()
      updateFromBuffer(buf0)
    } catch {
      // silent
    }
    pollTimer = window.setInterval(async () => {
      try {
        const buf = await client.getBuffer()
        updateFromBuffer(buf)
      } catch {
        // silent
      }
    }, 1000)
  })

  onBeforeUnmount(() => {
    clearInterval(pollTimer)
    client.close()
  })

  return {
    backgroundSet,
    blobTexts,
    blobColors
  }
}
