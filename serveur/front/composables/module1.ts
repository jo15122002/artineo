// File: serveur/front/composables/module1.ts
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

  const backgroundPath = ref<string>('')
  const x              = ref(0)
  const y              = ref(0)
  const diamPx         = ref(1)

  // ────────────────────────────────────────────────────────────────────────────
  // 3) VARIABLES DE “BONNE RÉPONSE” (ZONE + DURÉE)
  // ────────────────────────────────────────────────────────────────────────────
  const goodResponsePosition = { x: 160, y: 120 }
  const goodResponseZoneSize = 30
  const goodResponseStayTime = 2.0

  const inZone = ref(false)
  let entryTime: number | null = null
  let responseAlreadyValidated = false
  // ────────────────────────────────────────────────────────────────────────────

  // 4) fps & interval dynamique
  const fps      = ref(10)           // valeur par défaut
  let pollTimer: number | undefined

  // ────────────────────────────────────────────────────────────────────────────
  // 5) CALCUL DU STYLE CSS “filter” RELATIF À la bonne réponse
  // ────────────────────────────────────────────────────────────────────────────
  const filterStyle = computed(() => {
    // Coordonnées IR actuelles
    const curX = x.value
    const curY = y.value

    // dx, dy relatifs à la bonne réponse
    const dx = curX - goodResponsePosition.x
    const dy = curY - goodResponsePosition.y

    // Calcul du hue
    let hueVal = (dx / goodResponsePosition.x) * 180
    if (hueVal > 180) hueVal = 180
    if (hueVal < -180) hueVal = -180

    // Calcul de la saturation
    let satVal = 100 + (dy / goodResponsePosition.y) * 100
    if (satVal < 0) satVal = 0
    if (satVal > 200) satVal = 200

    // Calcul de la brightness
    let brightVal = 100 - (dy / goodResponsePosition.y) * 50
    if (brightVal < 50) brightVal = 50
    if (brightVal > 150) brightVal = 150

    return `hue-rotate(${hueVal.toFixed(1)}deg) saturate(${satVal.toFixed(0)}%) brightness(${brightVal.toFixed(0)}%)`
  })
  // ────────────────────────────────────────────────────────────────────────────

  // 6) CETTE PARTIE S’EXÉCUTE LORSQUE LE COMPOSANT MONTE
  onMounted(async () => {
    // a) fetchConfig incluant fps
    try {
      const cfg = await client.fetchConfig()
      if (cfg.background)      backgroundPath.value = cfg.background
      if (typeof cfg.fps === 'number' && cfg.fps > 0) {
        fps.value = cfg.fps
        console.log(`[Module1] FPS configuré : ${fps.value}`)
      }
    } catch (e) {
      console.error('[Module1] fetchConfig error', e)
    }

    // b) gestion WebSocket push
    client.onMessage((msg: any) => {
      console.log(`[Module1] WebSocket message: ${msg.action}`, msg.buffer)
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
    // WATCHER DE VALIDATION “BONNE RÉPONSE”
    watch([x, y], ([newX, newY]) => {
      const dx = newX - goodResponsePosition.x
      const dy = newY - goodResponsePosition.y
      const distance = Math.hypot(dx, dy)
      const now = performance.now() / 1000 // secondes

      if (distance <= goodResponseZoneSize) {
        if (!inZone.value) {
          inZone.value = true
          entryTime = now
          responseAlreadyValidated = false
          console.debug(`[Module1] Entrée zone cible à ${entryTime.toFixed(3)}s`)
        } else if (!responseAlreadyValidated && entryTime !== null) {
          if (now - entryTime >= goodResponseStayTime) {
            console.log('Bonne réponse validée ! (front)')
            responseAlreadyValidated = true
          }
        }
      } else {
        if (inZone.value) {
          console.debug(`[Module1] Sortie zone cible à ${(now).toFixed(3)}s`)
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
    // client.close() retiré : connexion partagée
  })

  // 7) expose fps si besoin
  return {
    backgroundPath,
    filterStyle,
    x, y, diamPx, fps,
    inZone,
    entryTime,
    responseAlreadyValidated,
  }
}
