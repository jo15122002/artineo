// front/composables/module3.ts
import { useNuxtApp } from '#app'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { BufferPayload } from '~/utils/ArtineoClient'

export default function useModule3() {
  // Stub SSR
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

  // États
  const assignments    = ref<Record<string, Record<string, string>>>({})
  const answers        = ref<Array<Record<string, string>>>([])
  const backgroundSet  = ref<number>(1)
  const blobTexts      = ref<string[]>(['', '', ''])
  const blobColors     = ref<string[]>(['', '', ''])

  let pollTimer: number

  // Retourne le label correspondant au code, insensible à la casse
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

  // Met à jour blobs depuis le buffer, en cherchant la carte dans toutes les slots
  function updateFromBuffer(buf: BufferPayload) {
    // 1) background
    if (buf.current_set && buf.current_set !== backgroundSet.value) {
      backgroundSet.value = buf.current_set
    }

    // 2) initialise à "Aucun" / orange
    const texts = ['Aucun', 'Aucun', 'Aucun']
    const colors = ['#FFA500', '#FFA500', '#FFA500']

    // 3) pour chaque catégorie, regarde si l'une des uidX correspond
    const keys = ['lieu','couleur','emotion'] as const
    const uidKeys = ['uid1','uid2','uid3'] as const
    const idx = (backgroundSet.value || 1) - 1
    keys.forEach((key, i) => {
      const map = assignments.value[`${key}s`] || {}
      for (const uk of uidKeys) {
        const code = buf[uk as keyof BufferPayload]
        if (code) {
          const label = lookupLabel(map, code as string)
          if (label !== 'Inconnu') {
            texts[i] = label
            const correct = answers.value[idx]?.[key]
            colors[i] = (code as string).toLowerCase() === correct?.toLowerCase()
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
    // a) fetchConfig (assignments + answers)
    try {
      const cfg = await client.fetchConfig()
      assignments.value = cfg.assignments || {}
      answers.value     = cfg.answers     || []
    } catch (e) {
      console.error('[Module3] fetchConfig error', e)
    }

    // b) WS push
    client.onMessage(msg => {
      if (msg.action === 'get_buffer') {
        updateFromBuffer(msg.buffer as BufferPayload)
      }
    })

    // c) initial + polling HTTP fallback
    try {
      const buf0 = await client.getBuffer()
      updateFromBuffer(buf0)
    } catch {
      // ignore
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
