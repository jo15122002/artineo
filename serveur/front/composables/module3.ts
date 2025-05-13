// front/composables/useModule3.ts
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { BufferPayload } from '~/utils/ArtineoClient'
import { useArtineo } from './useArtineo'

export default function useModule3() {
  const moduleId = 3
  const { fetchConfig, getBuffer, onMessage, close } = useArtineo(moduleId)

  // config
  const assignments = ref<Record<string, Record<string, string>>>({})
  const answers     = ref<Array<Record<string, string>>>([])

  // listes de mots par catégorie (uniquement pour le cas où on en aurait besoin)
  const wanted = {
    lieux:   ref<string[]>([]),
    couleurs:ref<string[]>([]),
    emotions:ref<string[]>([])
  }

  // UI
  const backgroundSet = ref(1)           // numéro de la feuille en cours
  const blobTexts     = ref(['','',''])  // textes à afficher dans les 3 blobs
  const blobColors    = ref(['','',''])  // couleurs de fond des 3 blobs

  let intervalId: number

  function updateFromBuffer(buf: BufferPayload) {
    // 1) mise à jour du background
    if (buf.current_set && buf.current_set !== backgroundSet.value) {
      backgroundSet.value = buf.current_set
    }

    // 2) textes et couleurs des blobs
    const keys = ['lieu','couleur','emotion'] as const
    const idx  = (buf.current_set || 1) - 1

    blobTexts.value = keys.map((key, i) => {
      const uid = buf[`uid${i+1}` as keyof BufferPayload]
      if (!uid) return 'Aucun'
      // on cherche dans assignments[key+'s']
      const mapping = assignments.value[`${key}s`] || {}
      const found = Object.entries(mapping).find(([,u]) => u === uid)
      return found ? found[0] : 'Inconnu'
    })

    blobColors.value = keys.map((key, i) => {
      const uid = buf[`uid${i+1}` as keyof BufferPayload]
      if (!uid) return '#FFA500'
      const correctUid = answers.value[idx]?.[key]
      return uid.toLowerCase() === correctUid?.toLowerCase()
        ? '#00FF00'
        : '#FF0000'
    })
  }

  onMounted(async () => {
    // 1) fetchConfig
    const cfg = await fetchConfig()
    assignments.value = cfg.assignments || {}
    answers.value     = cfg.answers     || []

    wanted.lieux.value    = Object.keys(assignments.value.lieux    || {})
    wanted.couleurs.value = Object.keys(assignments.value.couleurs || {})
    wanted.emotions.value = Object.keys(assignments.value.emotions || {})

    // 2) WS realtime
    onMessage(msg => {
      if (msg.action === 'get_buffer') updateFromBuffer(msg.buffer)
    })

    // 3) initial + polling
    const buf0 = await getBuffer()
    updateFromBuffer(buf0)
    intervalId = window.setInterval(async () => {
      const buf = await getBuffer()
      updateFromBuffer(buf)
    }, 1000)
  })

  onBeforeUnmount(() => {
    clearInterval(intervalId)
    close()
  })

  return {
    backgroundSet,
    blobTexts,
    blobColors,
  }
}
