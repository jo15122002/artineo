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
    onComplete?: () => void,
    idVideo?: string
  ) => void
}

export function useArtyManager(
  moduleId: number,
  containerRef: Ref<HTMLElement | null>
): UseArtyManagerReturn {
  const mediaList    = ref<MediaItem[]>([])
  const currentIndex = ref<number>(0)
  const playerEl     = ref<HTMLMediaElement | null>(null)
  const fullScreenVideoEl = ref<HTMLVideoElement | null>(null)

  const { public: { apiUrl } } = useRuntimeConfig()

  async function load() {
    console.log(`[ArtyManager][Module ${moduleId}] → Début de load()`)
    try {
      const resp = await fetch(`${apiUrl}/media?module=${moduleId}`)
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status} au lieu de 200`)
      }
      const json = await resp.json()
      const list: MediaItem[] = (json.medias || []).map((m: any) => {
        let fullUrl: string
        if (typeof m.url === 'string' && m.url.startsWith('/')) {
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
      // if (list.length > 0) {
      //   currentIndex.value = 0
      //   initPlayer(currentIndex.value)
      // }
    } catch (e) {
      console.error(`[ArtyManager][Module ${moduleId}] Erreur pendant load():`, e)
    }
  }

  function initPlayer(
    index: number,
    onStartCallback?: () => void,
    onCompleteCallback?: () => void,
    autoplay = false,
    idVideo?: string
  ) {
    const container = containerRef.value

    // Retirer l’audio/vidéo précédent
    if (playerEl.value) {
      playerEl.value.removeEventListener('play',  handlePlay)
      playerEl.value.removeEventListener('ended', handleEnded)
      container?.removeChild(playerEl.value)
      playerEl.value = null
    }
    if (fullScreenVideoEl.value) {
      fullScreenVideoEl.value.removeEventListener('play',  handlePlay)
      fullScreenVideoEl.value.removeEventListener('ended', handleEnded)
      document.body.removeChild(fullScreenVideoEl.value)
      fullScreenVideoEl.value = null
    }

    const info = mediaList.value[index]
    if (!info) {
      console.warn(`[ArtyManager] initPlayer: pas de média pour index=${index}`)
      return
    }

    function handlePlay() {
      console.log(`[ArtyManager][Module ${moduleId}] onStart() pour "${info.title}"`)
      onStartCallback && onStartCallback()
    }
    function handleEnded() {
      console.log(`[ArtyManager][Module ${moduleId}] onComplete() pour "${info.title}"`)
      onCompleteCallback && onCompleteCallback()
      if (fullScreenVideoEl.value) {
        fullScreenVideoEl.value.pause()
        document.body.removeChild(fullScreenVideoEl.value)
        fullScreenVideoEl.value = null
      }
    }

    if (info.type.startsWith('video/')) {
      // VIDÉO PLEIN ÉCRAN SANS CONTROLES, EN AUTOPLAY
      const vid = document.createElement('video')
      vid.src         = info.url
      vid.preload     = 'auto'
      vid.muted       = false
      vid.autoplay    = autoplay
      vid.playsInline = true

      // On applique la classe CSS au lieu des styles inline
      vid.classList.add('arty-fullscreen-video')

      vid.addEventListener('play',  handlePlay)
      vid.addEventListener('ended', handleEnded)

      document.body.appendChild(vid)
      if(idVideo) {
        vid.setAttribute('id', idVideo)
      }
      fullScreenVideoEl.value = vid
    }
    else {
      // AUDIO – invisible dans le containerRef
      if (!container) {
        console.warn('[ArtyManager] initPlayer: containerRef non défini, skip')
        return
      }
      const audio = document.createElement('audio')
      audio.src     = info.url
      audio.preload = 'auto'
      audio.muted   = false

      // Classe CSS pour cacher l’élément
      audio.classList.add('arty-audio-hidden')

      audio.addEventListener('play',  handlePlay)
      audio.addEventListener('ended', handleEnded)

      container.appendChild(audio)
      playerEl.value = audio
    }
  }

  function play() {
    if (playerEl.value) {
      playerEl.value.play().catch(err => {
        console.warn('[ArtyManager] play() audio bloqué :', err)
      })
    }
    if (fullScreenVideoEl.value) {
      fullScreenVideoEl.value.play().catch(err => {
        console.warn('[ArtyManager] play() vidéo bloqué :', err)
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

  function playByTitle(
    title: string,
    onStart?: () => void,
    onComplete?: () => void,
    idVideo?: string
  ) {
    const idx = mediaList.value.findIndex(m => m.title === title)
    if (idx < 0) {
      console.warn(`[ArtyManager] playByTitle("${title}") → média introuvable`)
      return
    }
    currentIndex.value = idx
    initPlayer(idx, onStart, onComplete, true, idVideo)
    play()
  }

  watch(
    () => containerRef.value,
    async (el) => {
      if (el) await load()
    },
    { immediate: true }
  )

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
