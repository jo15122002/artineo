// front/composables/module3.ts
import { useNuxtApp } from '#app'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { BufferPayload } from '~/utils/ArtineoClient'

export default function useModule3() {
  // 1️⃣ Stub SSR : rien à faire côté serveur
  if (!process.client) {
    const empty = ref<any>(null)
    return {
      backgroundSet: empty,
      blobTexts: empty,
      blobColors: empty
    }
  }

  const moduleId = 3
  const { $artineo } = useNuxtApp()
  if (typeof $artineo !== 'function') {
    throw new Error('Plugin $artineo non injecté — vérifie plugins/artineo.ts')
  }
  const client = $artineo(moduleId)

  // 2️⃣ États
  const assignments = ref<Record<string, Record<string, string>>>({})
  const answers     = ref<Array<Record<string, string>>>([])
  const backgroundSet = ref<number>(1)
  const blobTexts     = ref<string[]>(['', '', ''])
  const blobColors    = ref<string[]>(['', '', ''])

  let pollTimer: number

  // Met à jour les blobs depuis le buffer
  function updateFromBuffer(buf: BufferPayload) {
    // 1) background
    if (buf.current_set && buf.current_set !== backgroundSet.value) {
      backgroundSet.value = buf.current_set
    }
    // 2) textes & couleurs
    const keys = ['lieu','couleur','emotion'] as const
    const idx  = (backgroundSet.value || 1) - 1
    blobTexts.value = keys.map((key, i) => {
      const uid = buf[`uid${i+1}` as keyof BufferPayload]
      if (!uid) return 'Aucun'
      const map = assignments.value[`${key}s`] || {}
      const found = Object.entries(map).find(([, u]) => u === uid)
      return found ? found[0] : 'Inconnu'
    })
    blobColors.value = keys.map((key, i) => {
      const uid = buf[`uid${i+1}` as keyof BufferPayload]
      if (!uid) return '#FFA500'
      const correct = answers.value[idx]?.[key]
      return uid.toLowerCase() === correct?.toLowerCase() ? '#00FF00' : '#FF0000'
    })
  }

  onMounted(async () => {
    // a) fetchConfig (assignments + answers + éventuellement fps si tu veux)
    try {
      const cfg = await client.fetchConfig()
      console.log('[Module3] fetchConfig', cfg)
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
