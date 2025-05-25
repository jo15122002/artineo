// front/composables/module3.ts
import { useNuxtApp } from '#app'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { BufferPayload } from '~/utils/ArtineoClient'

export default function useModule3() {
  if (!process.client) {
    const backgroundSet = ref(1)
    const blobTexts     = ref<string[]>(['Aucun','Aucun','Aucun'])
    const blobColors    = ref<string[]>(['#FFA500','#FFA500','#FFA500'])
    return { backgroundSet, blobTexts, blobColors }
  }

  const moduleId = 3
  const { $artineo } = useNuxtApp()
  const client = $artineo(moduleId)

  const assignments   = ref<Record<string, Record<string, string>>>({})
  const answers       = ref<Array<Record<string, string>>>([])
  const backgroundSet = ref<number>(1)
  const blobTexts     = ref<string[]>(['', '', ''])
  const blobColors    = ref<string[]>(['', '', ''])

  let pollTimer: number

  const pluralMap: Record<string, string> = {
    lieu:    'lieux',
    couleur: 'couleurs',
    emotion: 'emotions'
  }

  // Normalise et retire les accents + met en minuscules
  function normalizeLabel(str: string): string {
    return str
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim()
      .toLowerCase()
  }

  // Inverse un mapping label→uid en uid→label (normalisé)
  function buildReverseMap(map: Record<string, string>) {
    const inv: Record<string, string> = {}
    for (const [label, uid] of Object.entries(map)) {
      inv[normalizeLabel(label)] = label
    }
    return inv
  }

  function lookupLabel(
    map: Record<string, string>,
    code: string
  ): string {
    const inv = buildReverseMap(map)
    return inv[code.toLowerCase()] || 'Inconnu'
  }

  function updateFromBuffer(buf: BufferPayload) {
    if (buf.current_set && buf.current_set !== backgroundSet.value) {
      backgroundSet.value = buf.current_set
    }

    const texts  = ['Aucun', 'Aucun', 'Aucun']
    const colors = ['#FFA500', '#FFA500', '#FFA500']

    const keys    = ['lieu','couleur','emotion'] as const
    const uidKeys = ['uid1','uid2','uid3'] as const
    const setIdx  = (backgroundSet.value || 1) - 1

    keys.forEach((key, i) => {
      const cat     = pluralMap[key]
      const mapCat  = assignments.value[cat] || {}
      const correct = answers.value[setIdx]?.[key]?.toLowerCase()

      for (const uk of uidKeys) {
        const code = buf[uk as keyof BufferPayload]
        if (typeof code === 'string') {
          const label = lookupLabel(mapCat, code)
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
    try {
      const cfg = await client.fetchConfig()
      assignments.value = cfg.assignments || {}
      answers.value     = cfg.answers     || []

      console.log('[Module3] Config fetched', cfg)
    } catch (e) {
      console.error('[Module3] fetchConfig error', e)
    }

    client.onMessage(msg => {
      if (msg.action === 'get_buffer') {
        updateFromBuffer(msg.buffer as BufferPayload)
      }
    })

    try {
      const buf0 = await client.getBuffer()
      updateFromBuffer(buf0)
    } catch {}

    pollTimer = window.setInterval(async () => {
      try {
        const buf = await client.getBuffer()
        updateFromBuffer(buf)
      } catch {}
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
