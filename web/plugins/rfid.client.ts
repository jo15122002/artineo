import { defineNuxtPlugin } from '#app'

// Déclarations de types pour le buffer et la config
interface ConfigResponse {
  config: {
    assignments: {
      lieux?: Record<string, string>
      couleurs?: Record<string, string>
      emotions?: Record<string, string>
    }
    answers: Array<{ lieu: string; couleur: string; emotion: string }>
  }
}

interface Buffer {
  current_set: number
  uid1: string | null
  uid2: string | null
  uid3: string | null
  button_pressed: boolean
}

export default defineNuxtPlugin(() => {
  const moduleId = 3
  const serverUrl = '127.0.0.1:8000'
  let assignments: ConfigResponse['config']['assignments']
  let answers: ConfigResponse['config']['answers']
  let wanted: {
    lieux: [string, string][]
    couleurs: [string, string][]
    emotions: [string, string][]
  }
  let ws: WebSocket
  let _lastBackgroundSet: number | null = null
  let _lastBuffer: Buffer = { current_set: 1, uid1: null, uid2: null, uid3: null, button_pressed: false }

  // Cache pour les SVG
  const svgCache: Record<string, string> = {}

  // 1️⃣ Récupère config + précharge SVG + lance WebSocket
  async function fetchConfig() {
    const res = await fetch(`http://${serverUrl}/config?module=${moduleId}`)
    const json: ConfigResponse = await res.json()
    assignments = json.config.assignments
    answers = json.config.answers

    wanted = {
      lieux: Object.entries(assignments.lieux || {}),
      couleurs: Object.entries(assignments.couleurs || {}),
      emotions: Object.entries(assignments.emotions || {})
    }

    await preloadSvgs()
    setupWebSocket()
    requestBuffer()
    changeBackground(1)

    setInterval(requestBuffer, 1000)
  }

  // 2️⃣ Précharge les SVG
  async function preloadSvgs() {
    const ids = ['blob1', 'blob2', 'blob3']
    await Promise.all(
      ids.map(id =>
        fetch(`./assets/${id}.svg`)
          .then(r => {
            if (!r.ok) throw new Error(`${id}.svg introuvable`)
            return r.text()
          })
          .then(text => { svgCache[id] = text })
          .catch(err => console.error(err))
      )
    )
    console.log('SVG préchargés', svgCache)
  }

  // 3️⃣ Initialise WebSocket
  function setupWebSocket() {
    ws = new WebSocket(`ws://${serverUrl}/ws`)
    ws.onopen = () => console.log('WS ouverte')
    ws.onmessage = e => {
      let msg
      try { msg = JSON.parse(e.data) } catch { return }
      if (msg.action === 'get_buffer') updateBlobs(msg.buffer)
    }
    ws.onclose = () => setTimeout(setupWebSocket, 3000)
  }

  // 4️⃣ Envoie la requête “get”
  function requestBuffer() {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ module: moduleId, action: 'get' }))
    }
  }

  // 5️⃣ Met à jour les blobs
  function updateBlobs(buf: Buffer) {
    ['blob1', 'blob2', 'blob3'].forEach((id, i) => {
      const el = document.getElementById(id) as HTMLElement
      const uid = buf[`uid${i+1}` as keyof Buffer] as string | null
      const arr = i === 0 ? wanted.lieux : i === 1 ? wanted.couleurs : wanted.emotions
      const word = uid ? (arr.find(([w, u]) => u === uid) || [])[0] : ''
      el.innerHTML = `<p class=\"blob-text\">${word || 'Aucun'}</p>`
    })

    if (buf.current_set !== _lastBuffer.current_set) changeBackground(buf.current_set)
    if (buf.button_pressed) highlightBlobs(buf)
    _lastBuffer = buf
  }

  // 6️⃣ Coloration
  function highlightBlobs(buf: Buffer) {
    const setIdx = buf.current_set - 1
    ['blob1', 'blob2', 'blob3'].forEach((id, i) => {
      const el = document.getElementById(id) as HTMLElement
      const uid = buf[`uid${i+1}` as keyof Buffer] as string | null
      const key = i === 0 ? 'lieu' : i === 1 ? 'couleur' : 'emotion'
      const correct = uid?.toLowerCase() === answers[setIdx][key].toLowerCase()
      const col = !uid ? '#FFA500' : correct ? '#BFFF8E' : '#eb6a49'
      const textColor = !uid ? '#000000' : correct ? '#000000' : '#ffffff'
      el.style.backgroundColor = col
      (el.firstChild as HTMLElement).style.color = textColor
    })
  }

  // 7️⃣ Change le fond
  function changeBackground(set: number) {
    if (set === _lastBackgroundSet) return
    _lastBackgroundSet = set
    fetch(`http://${serverUrl}/getAsset?module=${moduleId}&path=tableau${set}.png`)
      .then(res => { if (!res.ok) throw new Error('PNG introuvable'); return res.blob() })
      .then(blob => { document.body.style.backgroundImage = `url(${URL.createObjectURL(blob)})` })
      .catch(console.error)
  }

  // Lancement au chargement
  window.addEventListener('load', fetchConfig)
  window.addEventListener('beforeunload', () => ws?.close())
})
