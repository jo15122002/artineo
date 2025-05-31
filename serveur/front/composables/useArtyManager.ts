// front/composables/useArtyManager.ts
import { useRuntimeConfig } from '#app'
import { ref, watch, type Ref } from 'vue'

export interface MediaItem {
  title: string
  type:  string
  url:   string
}

export interface UseArtyManagerReturn {
  mediaList:     Ref<MediaItem[]>
  currentIndex:  Ref<number>
  load:          () => Promise<void>
  play:          () => void
  next:          () => void
  prev:          () => void
  playByTitle:   (
    title: string,
    onStart?: () => void,
    onComplete?: () => void
  ) => void
}

/**
 * useArtyManager gère la récupération et la lecture des médias (audio/vidéo)
 * pour un module donné. 
 *
 * @param moduleId     Identifiant numérique du module (ex. 3)
 * @param containerRef Réf vers le <div> qui accueillera le <audio> ou <video>
 */
export function useArtyManager(
  moduleId: number,
  containerRef: Ref<HTMLElement | null>
): UseArtyManagerReturn {
  // ─── 1) RÉFÉRENCES RÉACTIVES ───────────────────────────────────────────────────
  const mediaList    = ref<MediaItem[]>([])
  const currentIndex = ref<number>(0)
  const playerEl     = ref<HTMLMediaElement | null>(null)

  // Récupère apiUrl depuis runtimeConfig (ex. "http://localhost:8000")
  const { public: { apiUrl } } = useRuntimeConfig()

  // ─── 2) load() : fetch `<apiUrl>/media?module=…` ──────────────────────────────
  async function load() {
    console.log(`[ArtyManager][Module ${moduleId}] → Début de load()`)
    try {
      // On appelle l’endpoint media sur FastAPI
      const resp = await fetch(`${apiUrl}/media?module=${moduleId}`)
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status} au lieu de 200`)
      }
      const json = await resp.json()
      // On attend un objet { medias: [ { title, type, url }, … ] }
      const list: MediaItem[] = (json.medias || []).map((m: any) => {
        // Si url est relative (commence par '/assets'), on le préfixe avec apiUrl
        let fullUrl: string
        if (typeof m.url === 'string' && m.url.startsWith('/')) {
          // Exemple : "/assets/module3/Introduction.mp3" → "http://localhost:8000/assets/module3/Introduction.mp3"
          fullUrl = apiUrl + m.url
        } else {
          fullUrl = m.url
        }
        return {
          title: m.title,
          type:  m.type,
          url:   fullUrl
        }
      })

      console.log(`[ArtyManager]   Envoi GET ${apiUrl}/media?module=${moduleId}`)
      console.log(`[ArtyManager][Module ${moduleId}] Liste reçue → ${list.length} élément(s)`)
      list.forEach((m, i) => {
        console.log(`   [${i}] title="${m.title}", type="${m.type}", url="${m.url}"`)
      })

      mediaList.value = list
      if (list.length > 0) {
        currentIndex.value = 0
        initPlayer(currentIndex.value)
      }
    } catch (e) {
      console.error(`[ArtyManager][Module ${moduleId}] Erreur pendant load():`, e)
    }
  }

  // ─── 3) initPlayer() : (re)crée <audio> ou <video> pour l’index donné ─────────
  function initPlayer(
    index: number,
    onStartCallback?: () => void,
    onCompleteCallback?: () => void
  ) {
    const container = containerRef.value
    if (!container) {
      console.warn('[ArtyManager] initPlayer: containerRef non défini, skip')
      return
    }

    // Si un player existait, on le retire avec ses listeners
    if (playerEl.value) {
      playerEl.value.removeEventListener('play',  handlePlay)
      playerEl.value.removeEventListener('ended', handleEnded)
      container.removeChild(playerEl.value)
      playerEl.value = null
    }

    const info = mediaList.value[index]
    if (!info) {
      console.warn(`[ArtyManager] initPlayer: pas de média pour index=${index}`)
      return
    }

    // Selon le type MIME, on crée <video> ou <audio>
    let el: HTMLMediaElement
    if (info.type.startsWith('video/')) {
      el = document.createElement('video')
      // dimensions par défaut (modifiez si besoin)
      ;(el as HTMLVideoElement).width  = 640
      ;(el as HTMLVideoElement).height = 360
      el.controls = true
    } else {
      el = document.createElement('audio')
      // On cache l’audio, on n’affiche pas l’élément
      el.style.display = 'none'
    }

    el.src     = info.url
    el.preload = 'auto'
    el.muted   = false

    function handlePlay() {
      console.log(`[ArtyManager][Module ${moduleId}] onStart() pour "${info.title}"`)
      onStartCallback && onStartCallback()
    }
    function handleEnded() {
      console.log(`[ArtyManager][Module ${moduleId}] onComplete() pour "${info.title}"`)
      onCompleteCallback && onCompleteCallback()
    }

    el.addEventListener('play',  handlePlay)
    el.addEventListener('ended', handleEnded)

    container.appendChild(el)
    playerEl.value = el
  }

  // ─── 4) Fonctions de contrôle : play(), next(), prev() ───────────────────────
  function play() {
    if (playerEl.value) {
      playerEl.value.play().catch(err => {
        console.warn('[ArtyManager] play() bloqué :', err)
      })
    }
  }

  function next() {
    if (!mediaList.value.length) return
    let nxt = currentIndex.value + 1
    if (nxt >= mediaList.value.length) nxt = 0
    currentIndex.value = nxt
    initPlayer(nxt)
    play()
  }

  function prev() {
    if (!mediaList.value.length) return
    let prv = currentIndex.value - 1
    if (prv < 0) prv = mediaList.value.length - 1
    currentIndex.value = prv
    initPlayer(prv)
    play()
  }

  // ─── 5) playByTitle() : cherche le média par titre, l’initialise et le joue ──
  function playByTitle(
    title: string,
    onStart?: () => void,
    onComplete?: () => void
  ) {
    const idx = mediaList.value.findIndex(m => m.title === title)
    if (idx < 0) {
      console.warn(`[ArtyManager] playByTitle("${title}") → média introuvable`)
      return
    }
    currentIndex.value = idx
    initPlayer(idx, onStart, onComplete)
    play()
  }

  // ─── 6) Watch sur containerRef : dès qu’il existe, on appelle load() ────────
  watch(
    () => containerRef.value,
    async (el) => {
      if (el) {
        await load()
      }
    },
    { immediate: true }
  )

  // ─── 7) On retourne toutes les méthodes, y compris load() ───────────────────
  return {
    mediaList,
    currentIndex,
    load,
    play,
    next,
    prev,
    playByTitle
  }
}
