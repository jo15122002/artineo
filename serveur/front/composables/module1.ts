// serveur/front/composables/module1.ts
import { useNuxtApp } from '#app'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { BufferPayload } from '~/utils/ArtineoClient'

export default function useModule1() {
  // 1) Stub en SSR
  if (!process.client) {
    const stub = ref<any>(null)
    return {
      backgroundPath: stub,
      filterStyle: stub,
      x: stub,
      y: stub,
      diamPx: stub,
      // on renvoie aussi ces refs même s’ils ne sont pas utilisés en SSR
      inZone: stub,
      entryTime: stub,
      responseAlreadyValidated: stub,
    }
  }

  const moduleId = 1
  const { $artineo } = useNuxtApp()
  if (typeof $artineo !== 'function') {
    throw new Error('Plugin $artineo non injecté — vérifie plugins/artineo.ts')
  }
  const client = $artineo(moduleId)

  // 2) refs
  const backgroundPath = ref<string>('')
  const x              = ref(0)
  const y              = ref(0)
  const diamPx         = ref(1)

  // ────────────────────────────────────────────────────────────────────────────
  // 3) VARIABLES DE “BONNE RÉPONSE” (ZONE + DURÉE)   <<< MODIF
  // ────────────────────────────────────────────────────────────────────────────
  // Position cible (en pixels) sur la zone IR (résolution 320×240)
  const goodResponsePosition = { x: 160, y: 120 }
  // Rayon (en pixels) de la zone considérée comme “correcte”
  const goodResponseZoneSize = 30
  // Nombre de secondes à rester DANS la zone pour valider
  const goodResponseStayTime = 2.0

  // Variables d’état internes
  const inZone = ref(false)
  let entryTime: number | null = null
  let responseAlreadyValidated = false
  // ────────────────────────────────────────────────────────────────────────────

  // 4) fps & interval dynamique
  const fps      = ref(10)           // valeur par défaut
  let pollTimer: number | undefined

  // 5) style calculé
  const frameH = 240, minB = 50, maxB = 150
  const bright = computed(() => {
    const pct = (1 - y.value / frameH) * (maxB - minB) + minB
    return Math.min(Math.max(pct, minB), maxB)
  })
  const hue = computed(() => (x.value / 320) * 360)
  const sat = computed(() => (y.value / 240) * 200 + 50)
  const filterStyle = computed(
    () => `hue-rotate(${hue.value}deg) saturate(${sat.value}%) brightness(${bright.value}%)`
  )

  // 6) CETTE PARTIE S’EXÉCUTE LORSQUE LE COMPOSANT MONTE
  onMounted(async () => {
    // a) fetchConfig incluant fps
    try {
      const cfg = await client.fetchConfig()
      if (cfg.background)      backgroundPath.value = cfg.background
      if (typeof cfg.fps === 'number' && cfg.fps > 0) {
        fps.value = cfg.fps
      }
    } catch (e) {
      console.error('[Module1] fetchConfig error', e)
    }

    // b) gestion WebSocket push
    client.onMessage((msg: any) => {
      if (msg.action === 'get_buffer') {
        const buf = msg.buffer as BufferPayload
        x.value      = buf.x      ?? x.value
        y.value      = buf.y      ?? y.value
        diamPx.value = buf.diameter ?? diamPx.value
      }
    })

    // c) polling dynamique selon fps
    const pollIntervalMs = () => Math.round(1000 / fps.value)
    const apply = (buf: BufferPayload) => {
      x.value      = buf.x      ?? x.value
      y.value      = buf.y      ?? y.value
      diamPx.value = buf.diameter ?? diamPx.value
    }

    // initial + fallback HTTP
    try {
      const buf0 = await client.getBuffer()
      apply(buf0)
    } catch {}

    // lance le polling
    pollTimer = window.setInterval(async () => {
      try {
        const buf = await client.getBuffer()
        apply(buf)
      } catch {
        // ignore
      }
    }, pollIntervalMs())

    // ────────────────────────────────────────────────────────────────────────────
    // WATCHER DE VALIDATION “BONNE RÉPONSE”   <<< MODIF
    // À chaque fois que x ou y change, on vérifie si l’on entre/sort de la zone
    watch([x, y], ([newX, newY]) => {
      const dx = newX - goodResponsePosition.x
      const dy = newY - goodResponsePosition.y
      const distance = Math.hypot(dx, dy)
      const now = performance.now() / 1000 // secondes

      if (distance <= goodResponseZoneSize) {
        // L’utilisateur est DANS la zone
        if (!inZone.value) {
          // Entrée dans la zone : on démarre le chrono
          inZone.value = true
          entryTime = now
          responseAlreadyValidated = false
          console.log(`[Module1] Entrée zone à ${entryTime.toFixed(3)}s`)
        } else if (!responseAlreadyValidated && entryTime !== null) {
          // Si on reste dans la zone depuis assez longtemps, on valide une fois
          if (now - entryTime >= goodResponseStayTime) {
            console.log('Bonne réponse validée ! (front)')
            responseAlreadyValidated = true
          }
        }
      } else {
        // L’utilisateur est HORS de la zone : on réinitialise
        if (inZone.value) {
          console.log(`[Module1] Sortie zone à ${(now).toFixed(3)}s`)
        }
        inZone.value = false
        entryTime = null
        responseAlreadyValidated = false
      }
    })
    // ────────────────────────────────────────────────────────────────────────────

  })

  onBeforeUnmount(() => {
    if (pollTimer) clearInterval(pollTimer)
    client.close()
  })

  // 7) expose fps si besoin
  return {
    backgroundPath,
    filterStyle,
    x, y, diamPx, fps,
    // on peut aussi exposer les refs d’état si nécessaire :
    inZone,
    entryTime,
    responseAlreadyValidated,
  }
}
