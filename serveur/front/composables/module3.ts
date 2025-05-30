// front/composables/module3.tsimport { useNuxtApp, useRuntimeConfig } from '#app'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import type { BufferPayload } from '~/utils/ArtineoClient'

export default function useModule3() {
  // Stub SSR
  if (!process.client) {
    const backgroundSet  = ref<number>(1)
    const blobTexts      = ref<string[]>(['Aucun','Aucun','Aucun'])
    const states         = ref<Array<'default'|'correct'|'wrong'>>(['default','default','default'])
    const stateClasses   = computed(() => states.value.map(s => `state-${s}`))
    const pressedStates  = ref<boolean[]>([false,false,false])
    return { backgroundSet, blobTexts, stateClasses, pressedStates }
  }

  const moduleId        = 3
  const { $artineo }    = useNuxtApp()
  const { public: { apiUrl } } = useRuntimeConfig()
  const client          = $artineo(moduleId)

  const backgroundSet   = ref<number>(1)
  const blobTexts       = ref<string[]>(['Aucun','Aucun','Aucun'])
  const states          = ref<Array<'default'|'correct'|'wrong'>>(['default','default','default'])
  const stateClasses    = computed(() => states.value.map(s => `state-${s}`))
  const pressedStates   = ref<boolean[]>([false,false,false])
  let prevPressed       = false

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

  function updateFromBuffer(buf: BufferPayload) {
    // 1) Si on change de set : on remet tout à zéro
    if (buf.current_set && buf.current_set !== backgroundSet.value) {
      backgroundSet.value  = buf.current_set
      // états visuels
      states.value         = ['default','default','default']
      pressedStates.value  = [false,false,false]
      prevPressed          = false
    }

    // 2) Construire textes & couleurs pour affichage
    const texts   = ['Aucun','Aucun','Aucun']
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
        const code = buf[uk as keyof BufferPayload]
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

    // 3) À la première transition button_pressed true → afficher feedback
    if (buf.button_pressed && !prevPressed) {
      // 3a) on passe en correct/wrong
      states.value = colors.map(c =>
        c === '#00FF00' ? 'correct'
        : c === '#FF0000' ? 'wrong'
        : 'default'
      )
      // 3b) on enfonce tous les boutons
      pressedStates.value = [true, true, true]

      // 3c) après 2s, on relève les wrong et on garde enfoncés que les correct
      setTimeout(() => {
        states.value        = states.value.map(s => s === 'wrong' ? 'default' : s)
        pressedStates.value = states.value.map(s => s === 'correct')
      }, 2000)
    }

    prevPressed = !!buf.button_pressed
  }

  async function fetchBufferHttp(): Promise<BufferPayload> {
    const res = await fetch(`${apiUrl}/buffer?module=${moduleId}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const js  = await res.json() as { buffer: BufferPayload }
    return js.buffer
  }

  onMounted(async () => {
    // Charger assignments & answers
    try {
      const cfg = await client.fetchConfig()
      ;(client as any).assignments = cfg.assignments || {}
      ;(client as any).answers     = cfg.answers     || []
    } catch {}

    // WS push & HTTP polling
    client.onMessage((msg: any) => {
      if (msg.action === 'get_buffer') {
        updateFromBuffer(msg.buffer as BufferPayload)
      }
    })

    // fallback initial + polling
    try {
      updateFromBuffer(await fetchBufferHttp())
    } catch {}
    const poll = setInterval(async () => {
      try { updateFromBuffer(await fetchBufferHttp()) } catch {}
    }, 1000)

    onBeforeUnmount(() => clearInterval(poll))
  })

  return { backgroundSet, blobTexts, stateClasses, pressedStates }
}
