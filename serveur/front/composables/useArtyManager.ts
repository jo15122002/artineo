// composables/useArtyManager.ts
import { ref } from 'vue'
import { useRuntimeConfig } from '#app'

export interface MediaItem {
  url:    string
  type:   string
  title:  string
}

export function useArtyManager(moduleId: number, target: HTMLElement | null) {
  const { public: { apiUrl } } = useRuntimeConfig()
  const mediaList = ref<MediaItem[]>([])
  const currentIndex = ref(0)
  let player: HTMLMediaElement | null = null

  async function load() {
    const res = await fetch(`${apiUrl}/media?module=${moduleId}`)
    const js  = await res.json() as { media: MediaItem[] }
    mediaList.value = js.media
    initPlayer()
  }

  function initPlayer() {
    if (!target) return
    target.innerHTML = ''
    const m = mediaList.value[currentIndex.value]
    player = document.createElement(m.type.startsWith('video/') ? 'video' : 'audio')
    player.src = `${apiUrl.replace(/^http/, 'http')}${m.url}`
    player.controls = true
    player.style.maxWidth = '100%'
    target.appendChild(player)
  }

  function play() {
    if (!player) initPlayer()
    player?.play()
  }
  function next() {
    if (currentIndex.value + 1 < mediaList.value.length) {
      currentIndex.value++
      initPlayer()
      play()
    }
  }
  function prev() {
    if (currentIndex.value > 0) {
      currentIndex.value--
      initPlayer()
      play()
    }
  }

  return { load, play, next, prev, mediaList, currentIndex }
}
