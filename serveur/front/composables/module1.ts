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
    const refDiam = 40  // diamètre en px pour lequel on veut sat=100%

    let satVal = 100 + ((diamPx.value - refDiam) / refDiam) * 100
    // clamp entre 0 et 200
    if (satVal < 0)   satVal = 0
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

    startTimer()
    console.log('[Module1] Initialisation du module 1')
    try {
      const cfg = await client.fetchConfig()
      if (cfg.background)      backgroundPath.value = cfg.background
      if (typeof cfg.fps === 'number' && cfg.fps > 0) {
        fps.value = cfg.fps + 1
        console.log(`[Module1] FPS configuré : ${fps.value}`)
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

   // 8) Couleur du timer
    const TIMER_DURATION = 60 // secondes
    const timerSeconds = ref<number>(TIMER_DURATION)
    let timerInterval: number | undefined = undefined

      function startTimer() {
        // réinitialise la valeur et stoppe un éventuel timer en cours
        if (timerInterval) {
          clearInterval(timerInterval)
        }
        timerSeconds.value = TIMER_DURATION
        // décrémente chaque seconde
        timerInterval = window.setInterval(() => {
          // on décompte et on s'assure de ne pas passer sous 0
          timerSeconds.value = Math.max(timerSeconds.value - 1, 0)
          if (timerSeconds.value === 0 && timerInterval) {
            clearInterval(timerInterval)
          }
        }, 1000)
      }

    function hexToRgb(hex: string) {
      const h = hex.replace('#','')
      const bigint = parseInt(h, 16)
      return {
        r: (bigint >> 16) & 0xFF,
        g: (bigint >> 8)  & 0xFF,
        b:  bigint        & 0xFF,
      }
    }
    function rgbToHex(r: number, g: number, b: number) {
      const hr = r.toString(16).padStart(2, '0')
      const hg = g.toString(16).padStart(2, '0')
      const hb = b.toString(16).padStart(2, '0')
      return `#${hr}${hg}${hb}`
    }
    function lerp(a: number, b: number, t: number) {
      return a + (b - a) * t
    }

    const colorStops = [
        { p: 1.0, color: '#2626FF' },
        { p: 0.6, color: '#FA81C3' },
        { p: 0.3, color: '#FA4923' }
      ] as const
    
    const timerColor = computed(() => {
      // ratio entre 0 et 1
      const pct = timerSeconds.value / TIMER_DURATION
      // on parcourt chaque segment [i]→[i+1]
      for (let i = 0; i < colorStops.length - 1; i++) {
        const { p: p0, color: c0 } = colorStops[i]
        const { p: p1, color: c1 } = colorStops[i+1]
        if (pct <= p0 && pct >= p1) {
          // t = 0 à p0  → couleur c0
          // t = 1 à p1  → couleur c1
          const t = (p0 - pct) / (p0 - p1)
          const rgb0 = hexToRgb(c0)
          const rgb1 = hexToRgb(c1)
          const r = Math.round(lerp(rgb0.r, rgb1.r, t))
          const g = Math.round(lerp(rgb0.g, rgb1.g, t))
          const b = Math.round(lerp(rgb0.b, rgb1.b, t))
          return rgbToHex(r, g, b)
        }
      }
      // fallback
      return colorStops[colorStops.length - 1].color
    })

    // computed pour formater en M:SS
    const timerText = computed(() => {
      const m = Math.floor(timerSeconds.value / 60);
      const s = timerSeconds.value % 60;
      return `${m}:${String(s).padStart(2, '0')}`;
    });

  onBeforeUnmount(() => {
    if (pollTimer) clearInterval(pollTimer)
    if (timerInterval) clearInterval(timerInterval)
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
    timerColor,
    timerText
  }
}
