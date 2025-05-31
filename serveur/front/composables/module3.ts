// front/composables/module3.ts
import { useNuxtApp, useRuntimeConfig } from '#app'
import { computed, onBeforeUnmount, onMounted, ref, type Ref } from 'vue'
import type ArtyPlayerComponent from '~/components/ArtyPlayer.vue'
import type { BufferPayload } from '~/utils/ArtineoClient'

/**
 * useModule3 : gère la logique 3RFID et permet de piloter ArtyPlayer via playerRef.
 *
 * @param playerRef  Référence vers l’instance de <ArtyPlayer> (ou null avant le montage)
 */
export default function useModule3(
  playerRef: Ref<InstanceType<typeof ArtyPlayerComponent> | null>
) {
  // ─── 1. Stub SSR ───────────────────────────────────────────────────────────
  if (!process.client) {
    const backgroundSet  = ref<number>(1)
    const blobTexts      = ref<string[]>(['Aucun','Aucun','Aucun'])
    const states         = ref<Array<'default'|'correct'|'wrong'>>(['default','default','default'])
    const stateClasses   = computed(() => states.value.map(s => `state-${s}`))
    const pressedStates  = ref<boolean[]>([false,false,false])
    return {
      backgroundSet,
      blobTexts,
      stateClasses,
      pressedStates,
      // Ajout d’une fonction no-op pour playIntro en SSR
      playIntro: () => {}
    }
  }

  // ─── 2. Initialisation du composable (client, refs, etc.) ───────────────────
  const moduleId      = 3
  const { $artineo }  = useNuxtApp()
  const { public: { apiUrl } } = useRuntimeConfig()
  const client        = $artineo(moduleId)

  // Réfs pour l’affichage et le feedback 3RFID
  const backgroundSet  = ref<number>(1)
  const blobTexts      = ref<string[]>(['Aucun','Aucun','Aucun'])
  const states         = ref<Array<'default'|'correct'|'wrong'>>(['default','default','default'])
  const stateClasses   = computed(() => states.value.map(s => `state-${s}`))
  const pressedStates  = ref<boolean[]>([false,false,false])
  let prevPressed      = false

  // Mappage catégories → champ config
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

  // ─── 3. Mise à jour depuis le buffer retourné par le serveur ─────────────────
  function updateFromBuffer(buf: BufferPayload) {
    // 3.1) Si changement de set, reset visuel
    if (buf.current_set && buf.current_set !== backgroundSet.value) {
      backgroundSet.value  = buf.current_set
      states.value         = ['default','default','default']
      pressedStates.value  = [false,false,false]
      prevPressed          = false
    }

    // 3.2) Construit textes (blobTexts) & couleurs (states) d’après les UIDs
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

    // 3.3) À la transition button_pressed true → afficher feedback visuel
    if (buf.button_pressed && !prevPressed) {
      // a) on passe les états en correct/wrong
      states.value = colors.map(c =>
        c === '#00FF00' ? 'correct'
        : c === '#FF0000' ? 'wrong'
        : 'default'
      )
      // b) on met tous les boutons enfoncés
      pressedStates.value = [true, true, true]

      // c) après 2s, on relève les wrong, on laisse down les correct
      setTimeout(() => {
        states.value        = states.value.map(s => s === 'wrong' ? 'default' : s)
        pressedStates.value = states.value.map(s => s === 'correct')
      }, 2000)
    }

    prevPressed = !!buf.button_pressed
  }

  // ─── 4. Récupération via HTTP (fallback) ────────────────────────────────────
  async function fetchBufferHttp(): Promise<BufferPayload> {
    const res = await fetch(`${apiUrl}/buffer?module=${moduleId}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const js  = await res.json() as { buffer: BufferPayload }
    return js.buffer
  }

  // ─── 5. Fonction pour jouer « Introduction.mp3 » via le playerRef ──────────
  function playIntro() {
    const titre = 'Introduction.mp3'
    if (playerRef.value) {
      console.log(`[useModule3] playIntro() → demande playByTitle("${titre}")`)
      playerRef.value.playByTitle(titre)
    } else {
      console.warn('[useModule3] playIntro() → playerRef.value est null, impossible de jouer')
    }
  }

  // ─── 6. Cycle de vie de Vue : onMounted / onBeforeUnmount ───────────────────
  onMounted(async () => {
    // 6.1) Charger assignments & answers depuis fetchConfig()
    try {
      const cfg = await client.fetchConfig()
      ;(client as any).assignments = cfg.assignments || {}
      ;(client as any).answers     = cfg.answers     || []
    } catch (e) {
      console.warn('[useModule3] fetchConfig error', e)
    }

    // 6.2) Écoute push WebSocket et HTTP polling
    client.onMessage((msg: any) => {
      if (msg.action === 'get_buffer') {
        updateFromBuffer(msg.buffer as BufferPayload)
      }
    })

    // 6.3) initial + polling HTTP fallback
    try {
      updateFromBuffer(await fetchBufferHttp())
    } catch (e) {
      console.warn('[useModule3] fetchBufferHttp initial error', e)
    }
    const poll = setInterval(async () => {
      try {
        updateFromBuffer(await fetchBufferHttp())
      } catch {
        // ignore
      }
    }, 1000)

    onBeforeUnmount(() => clearInterval(poll))
  })

  // ─── 7. URL d’arrière-plan pour l’image tableauX.png ────────────────────────
  const backgroundUrl = computed(
    () => `${apiUrl}/getAsset?module=3&path=tableau${backgroundSet.value}.png`
  )

  // ─── 8. On retourne tout ce dont le composant a besoin ──────────────────────
  return {
    backgroundSet,
    blobTexts,
    stateClasses,
    pressedStates,
    backgroundUrl,
    playIntro
  }
}
