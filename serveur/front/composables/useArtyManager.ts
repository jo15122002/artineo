// composables/useArtyManager.ts
import { useRuntimeConfig } from '#app'
import { ref, watch, type Ref } from 'vue'

export interface MediaItem {
  url:    string
  type:   string
  title:  string
}

/**
 * useArtyManager :
 *   - moduleId : numéro du module (pour GET /media?module=…)
 *   - targetRef : Ref<HTMLElement|null> pointant vers l’élément DOM où injecter <audio>/<video>
 */
export function useArtyManager(
  moduleId: number,
  targetRef: Ref<HTMLElement | null>
) {
  const { public: { apiUrl } } = useRuntimeConfig()

  // liste des médias renvoyée par l'API
  const mediaList = ref<MediaItem[]>([])
  // index du média actuellement chargé
  const currentIndex = ref(0)
  // référence au <audio> ou <video> créé dans le DOM
  let player: HTMLMediaElement | null = null

  // --- 1. initPlayer() : reconstruit le <audio>/<video> dans targetRef.value ---
  function initPlayer() {
    const target = targetRef.value
    if (!target) {
      console.warn(`[ArtyManager][Module ${moduleId}] initPlayer() → targetRef.value est null`)
      player = null
      return
    }

    // vide le conteneur
    target.innerHTML = ''

    if (!mediaList.value.length) {
      console.log(`[ArtyManager][Module ${moduleId}] Aucun média trouvé pour ce module`)
      player = null
      return
    }

    const m = mediaList.value[currentIndex.value]
    console.log(
      `[ArtyManager][Module ${moduleId}] initPlayer() → index=${currentIndex.value}, ` +
      `title="${m.title}", type="${m.type}", url="${m.url}"`
    )

    // créer <video> ou <audio> selon le type MIME
    player = document.createElement(
      m.type.startsWith('video/') ? 'video' : 'audio'
    )
    player.src = `${apiUrl.replace(/^http/, 'http')}${m.url}`
    player.controls = true
    player.style.maxWidth = '100%'

    target.appendChild(player)
  }

  // --- 2. load() : appel GET /media?module=… puis initPlayer() ---
  async function load() {
    console.log(`[ArtyManager][Module ${moduleId}] → Début de load()`)
    try {
      const url = `${apiUrl}/media?module=${moduleId}`
      console.log(`[ArtyManager]   Envoi GET ${url}`)
      const res = await fetch(url)
      if (!res.ok) {
        console.warn(
          `[ArtyManager][Module ${moduleId}] GET /media a échoué → status ${res.status}`
        )
        return
      }
      const js = (await res.json()) as { media: MediaItem[] }
      mediaList.value = js.media || []

      console.log(
        `[ArtyManager][Module ${moduleId}] Liste reçue → ${mediaList.value.length} élément(s)`
      )
      mediaList.value.forEach((m, i) => {
        console.log(`   [${i}] title="${m.title}", type="${m.type}", url="${m.url}"`)
      })

      // Dès que la liste est chargée, on initialise le player (si targetRef.value existe déjà)
      if (targetRef.value) {
        initPlayer()
      }
    } catch (err) {
      console.error(
        `[ArtyManager][Module ${moduleId}] Erreur pendant load():`, err
      )
    }
  }

  // --- 3. Fonctions basiques de lecture ---
  function play() {
    if (!player) {
      console.log(`[ArtyManager][Module ${moduleId}] play() → player non initialisé, appel initPlayer()`)
      initPlayer()
    }
    console.log(`[ArtyManager][Module ${moduleId}] play() → Lecture du média index=${currentIndex.value}`)
    player?.play()
  }

  function next() {
    if (currentIndex.value + 1 < mediaList.value.length) {
      currentIndex.value++
      console.log(`[ArtyManager][Module ${moduleId}] next() → Passage à index=${currentIndex.value}`)
      initPlayer()
      play()
    } else {
      console.log(`[ArtyManager][Module ${moduleId}] next() → Déjà au dernier média`)
    }
  }

  function prev() {
    if (currentIndex.value > 0) {
      currentIndex.value--
      console.log(`[ArtyManager][Module ${moduleId}] prev() → Passage à index=${currentIndex.value}`)
      initPlayer()
      play()
    } else {
      console.log(`[ArtyManager][Module ${moduleId}] prev() → Déjà au premier média`)
    }
  }

  // --- 4. playByTitle(title) : recherche par title et joue le média ---
  function playByTitle(title: string) {
    console.log(`[ArtyManager][Module ${moduleId}] playByTitle("${title}") appelé`)
    const idx = mediaList.value.findIndex(item => item.title === title)
    if (idx === -1) {
      console.warn(
        `[ArtyManager][Module ${moduleId}] Aucun média trouvé pour le titre "${title}"`
      )
      return
    }
    currentIndex.value = idx
    console.log(
      `[ArtyManager][Module ${moduleId}] Index mis à jour → ${idx}, ` +
      `title="${mediaList.value[idx].title}"`
    )
    initPlayer()
    play()
  }

  // --- 5. Si targetRef.value change (montage du <div>), on peut initPlayer() automatiquement ---
  watch(targetRef, (el) => {
    if (el && mediaList.value.length) {
      console.log(`[ArtyManager][Module ${moduleId}] watch(targetRef) → nouvel élément, appel initPlayer()`)
      initPlayer()
    }
  })

  return {
    load,
    play,
    next,
    prev,
    playByTitle,
    mediaList,
    currentIndex
  }
}
