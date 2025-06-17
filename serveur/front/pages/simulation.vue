<template>
  <div class="simulation-dashboard">
    <h1>Simulateur de modules</h1>
    <div v-for="mod in moduleIds" :key="mod" class="simulator-card">
      <h2>Module {{ mod }}</h2>

      <!-- MODULE 1 -->
      <div v-if="mod === 1" class="controls module1-controls">
        <div class="ir-area-container">
          <div class="ir-area" @mousedown="onIrAreaMouseDown" @mouseup="onIrAreaMouseUp" @mouseleave="onIrAreaMouseUp"
            @mousemove="onIrAreaMouseMove">
            <div v-if="module1Fields.clicked" class="ir-marker"
              :style="{ left: module1Fields.x + 'px', top: module1Fields.y + 'px' }" />
          </div>
          <div class="ir-coords">
            X: {{ module1Fields.x }}, Y: {{ module1Fields.y }}
          </div>
        </div>
        <label class="slider-label">
          Diamètre :
          <input type="range" v-model.number="module1Fields.diameter" min="1" max="200" />
          <span>{{ module1Fields.diameter }} px</span>
        </label>
      </div>

      <!-- MODULE 2 -->
      <div v-else-if="mod === 2" class="controls module2-controls">
        <label>
          rotX :
          <input type="range" v-model.number="module2Fields.rotX" :min="-6.28" :max="6.28" step="0.01" />
          <span>{{ module2Fields.rotX.toFixed(2) }}</span>
        </label>
        <label>
          rotY :
          <input type="range" v-model.number="module2Fields.rotY" :min="-6.28" :max="6.28" step="0.01" />
          <span>{{ module2Fields.rotY.toFixed(2) }}</span>
        </label>
        <label>
          rotZ :
          <input type="range" v-model.number="module2Fields.rotZ" :min="-6.28" :max="6.28" step="0.01" />
          <span>{{ module2Fields.rotZ.toFixed(2) }}</span>
        </label>
      </div>

      <!-- MODULE 3 -->
      <div v-else-if="mod === 3" class="controls module3-controls">
        <label>
          Lieu :
          <select v-model="module3Fields.uid1">
            <option value="">-- Choisir un lieu --</option>
            <option v-for="label in module3Config.wanted_assignments.lieux" :key="label"
              :value="module3Config.assignments.lieux[label]">
              {{ label }}
            </option>
          </select>
        </label>
        <label>
          Couleur :
          <select v-model="module3Fields.uid2">
            <option value="">-- Choisir une couleur --</option>
            <option v-for="label in module3Config.wanted_assignments.couleurs" :key="label"
              :value="module3Config.assignments.couleurs[label]">
              {{ label }}
            </option>
          </select>
        </label>
        <label>
          Émotion :
          <select v-model="module3Fields.uid3">
            <option value="">-- Choisir une émotion --</option>
            <option v-for="label in module3Config.wanted_assignments.emotions" :key="label"
              :value="module3Config.assignments.emotions[label]">
              {{ label }}
            </option>
          </select>
        </label>
        <label>
          Set courant :
          <select v-model.number="module3Fields.current_set">
            <option v-for="(_, i) in module3Config.answers" :key="i" :value="i + 1">
              Set {{ i + 1 }}
            </option>
          </select>
        </label>
        <label>
          Bouton pressé :
          <input type="checkbox" v-model="module3Fields.button_pressed" />
        </label>

        <label class="slider-label">
          Timer :
          <input type="range" v-model.number="module3Fields.timer" min="0" max="60" />
          <span>{{ formattedTimer }}</span>
        </label>
      </div>

      <!-- MODULE 4 : Sandbox avec palette d'objets -->
      <div v-else class="controls module4-controls">
        <div class="remove-buttons">
          <button @click="removeAll()">Enlever tout</button>
          <button @click="removeObjects()">Enlever objets</button>
          <button @click="removeBackground()">Enlever fond</button>
        </div>
        <div class="module4-container">
          <div>
            <div class="button-selector">
              <span>Overlay Button :</span>
              <button v-for="id in Object.keys(buttonColors)" :key="id" :class="{ active: currentButton === +id }"
                @click="currentButton = +id">
                Button {{ id }}
              </button>
            </div>

            <!-- Palette Backgrounds -->
            <div class="palette backgrounds-palette">
              <h3>Backgrounds</h3>
              <button v-for="bg in backgrounds" :key="bg.src" @click="setBackground(bg)"
                :class="{ selected: currentBackground?.src === bg.src }">
                <img :src="bg.src" class="palette-icon" />
                {{ bg.name }}
              </button>
            </div>

            <!-- Palette Objets -->
            <div class="palette objects-palette">
              <h3>Objets</h3>
              <button v-for="obj in objectItems" :key="obj.src" class="draggable-item"
                @pointerdown.prevent="startDrag(obj, $event)">
                <img :src="obj.src" class="palette-icon" draggable="false" />
                {{ obj.name }}
              </button>
            </div>
          </div>

          <!-- Sandbox -->
          <div class="sandbox" :ref="setSandbox">
            <img v-if="currentBackground" :src="currentBackground.src" class="background-image" />
            <img v-for="o in placedObjects" :key="o.id" class="placed-object" :src="o.src" :style="{
              left: o.x + 'px',
              top: o.y + 'px',
              width: getScaledSize(o.src).width + 'px',
              height: getScaledSize(o.src).height + 'px'
            }" />
            <div class="sandbox-overlay" :style="{ backgroundColor: buttonColors[currentButton] }" />
            <!-- aperçu pendant drag -->
            <img v-if="dragPreview" :src="dragPreview.src" class="drag-preview" :style="{
              left: dragPreview.x + 'px',
              top: dragPreview.y + 'px',
              width: getScaledSize(dragPreview.src).width + 'px',
              height: getScaledSize(dragPreview.src).height + 'px'
            }" />
          </div>
        </div>
      </div>

      <!-- Toggle Envoi continu -->
      <label class="switch">
        Envoi continu
        <input type="checkbox" v-model="streaming[mod]" />
        <span class="slider round"></span>
      </label>

      <!-- Contrôle du timer -->
      <div class="timer-controls">
        <button @click="controlTimer(mod, 'reset')">Reset Timer</button>
        <button @click="controlTimer(mod, 'pause')">Pause Timer</button>
        <button @click="controlTimer(mod, 'resume')">Resume Timer</button>
      </div>

      <!-- Boutons d'action -->
      <div class="button-row">
        <button @click="sendById(mod)">Envoyer buffer</button>
        <button @click="retrieveBuffer(mod)">Récupérer buffer</button>
      </div>

      <!-- Affichage du dernier buffer -->
      <div class="output">
        <h3>Dernier buffer reçu</h3>
        <pre>{{ buffers[mod] }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useArtineo } from '~/composables/useArtineo'

const moduleIds = [1, 2, 3, 4]
const clients = reactive<Record<number, ReturnType<typeof useArtineo>>>({})
const buffers = reactive<Record<number, string>>({})

// MODULE 1 fields
const module1Fields = reactive({
  x: 0,
  y: 0,
  diameter: 10,
  clicked: false,
  isDragging: false
})

// MODULE 2 fields
const module2Fields = reactive({
  rotX: 0,
  rotY: 0,
  rotZ: 0
})

// MODULE 3 fields & config
const module3Fields = reactive({
  uid1: '',
  uid2: '',
  uid3: '',
  current_set: 1,
  button_pressed: false,
  timer: 60
})
const module3Config = reactive({
  answers: [] as any[],
  wanted_assignments: { lieux: [] as string[], couleurs: [] as string[], emotions: [] as string[] },
  assignments: { lieux: {} as Record<string, string>, couleurs: {} as Record<string, string>, emotions: {} as Record<string, string> }
})

// MODULE 4 – import des PNG SSR-compatible
const objectModules = import.meta.glob<string>(
  '~/assets/modules/4/images/objects/*.png',
  { eager: true, as: 'url' }
)
const allItems = Object.entries(objectModules).map(([path, url]) => ({
  name: path.split('/').pop()!.replace('.png', ''),
  src: url
}))
const backgrounds = computed(() => allItems.filter(i => i.name.startsWith('landscape_')))
const objectItems = computed(() => allItems.filter(i => !i.name.startsWith('landscape_')))
const imageSizes = reactive<Record<string, { width: number; height: number }>>({})

const currentBackground = ref<{ src: string; id: string } | null>(null)
const placedObjects = reactive<Array<{ src: string; x: number; y: number; id: string }>>([])

const draggingSrc = ref<string | null>(null)
const dragPreview = ref<{ src: string; x: number; y: number } | null>(null)
const scale = 16

const newBackgroundsBuf = reactive<{ src: string; id: string }[]>([])
const removeBackgroundsBuf = reactive<string[]>([])
const removeObjectsBuf = reactive<string[]>([])
const newObjectsBuf = reactive<{ src: string; x: number; y: number; id: string }[]>([])


const buttonColors: Record<number, string> = {
  1: 'rgba(83, 160, 236, 0.2)',
  2: 'rgba(252, 191, 0, 0.2)',
  3: 'rgba(147, 146, 183, 0.6)'
}
const currentButton = ref<number>(1)

// ─── MODULE 4 drag’n’drop ─────────────────────────────────────────────

const sandbox = ref<HTMLElement | null>(null)

function setSandbox(el: Element | ComponentPublicInstance | null) {
  sandbox.value = el as HTMLElement | null
}

function lockScroll() {
  const dash = document.querySelector<HTMLElement>('.simulation-dashboard')
  if (dash) dash.style.overflowY = 'hidden'
}

function unlockScroll() {
  const dash = document.querySelector<HTMLElement>('.simulation-dashboard')
  if (dash) dash.style.overflowY = ''
}

// Ce handler est appelé à chaque move, pour repositionner l’aperçu
function onPointerMove(evt: PointerEvent) {
  if (!draggingSrc.value || !sandbox.value) return
  const rect = sandbox.value.getBoundingClientRect()
  const { width, height } = getScaledSize(draggingSrc.value)
  dragPreview.value = {
    src: draggingSrc.value,
    x: Math.round(evt.clientX - rect.left - width / 2),
    y: Math.round(evt.clientY - rect.top - height / 2)
  }
}

// Quand on relâche, on crée l’objet dans le sandbox et on nettoie
function endDrag(evt: PointerEvent) {
  console.log('contenu de sandbox.value →', sandbox.value)
  if (draggingSrc.value && sandbox.value) {
    const rect = sandbox.value.getBoundingClientRect()
    const size = getScaledSize(draggingSrc.value)
    placedObjects.push({
      src: draggingSrc.value,
      x: Math.round(evt.clientX - rect.left - size.width / 2),
      y: Math.round(evt.clientY - rect.top - size.height / 2),
      id: `obj-${Date.now()}`
    })
  }
  // cleanup
  dragPreview.value = null
  draggingSrc.value = null
  unlockScroll()
}

// Démarre le drag : on bloque le scroll et on bind window‐events
function startDrag(obj: { src: string }, evt: PointerEvent) {
  draggingSrc.value = obj.src
  lockScroll()

  // tant que l’on n’a pas relâché, on suit le pointeur partout
  const move = (e: PointerEvent) => onPointerMove(e)
  const up = (e: PointerEvent) => {
    endDrag(e)
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
    window.removeEventListener('pointercancel', up)
  }

  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
  window.addEventListener('pointercancel', up)
}

// --- Fonctions de sélection / placement ---
function setBackground(bg: { src: string }) {
  if (currentBackground.value) {
    removeBackgroundsBuf.push(currentBackground.value.id)
    const idx = newBackgroundsBuf.findIndex(b => b.id === currentBackground.value!.id)
    if (idx >= 0) newBackgroundsBuf.splice(idx, 1)
  }
  const id = `background-${Date.now()}`
  currentBackground.value = { src: bg.src, id }
  newBackgroundsBuf.splice(0)
  newBackgroundsBuf.push({ src: bg.src, id })
}

function removeBackground() {
  if (!currentBackground.value) return
  removeBackgroundsBuf.push(currentBackground.value.id)
  // on retire le fond de l’affichage
  currentBackground.value = null
  // on enlève l’éventuel newBuffer
  const idx = newBackgroundsBuf.findIndex(b => b.id === currentBackground.value?.id)
  if (idx >= 0) newBackgroundsBuf.splice(idx, 1)
}

function removeAll() {
  removeBackground()
  removeObjects()
}

// Streaming toggles & timers
// computed pour formater "M:SS"
const streaming = reactive<Record<number, boolean>>({ 1: false, 2: false, 3: false, 4: false })
const intervals = reactive<Record<number, number | null>>({ 1: null, 2: null, 3: null, 4: null })

const formattedTimer = computed(() => {
  const s = Math.max(0, Math.min(60, module3Fields.timer))
  const m = Math.floor(s / 60)
  const ss = (s % 60).toString().padStart(2, '0')
  return `${m}:${ss}`
})

// Gestion IR Module 1
function onIrAreaMouseDown(evt: MouseEvent) {
  module1Fields.isDragging = true
  updateIrPosition(evt)
}
function onIrAreaMouseUp() {
  module1Fields.isDragging = false
}
function onIrAreaMouseMove(evt: MouseEvent) {
  if (module1Fields.isDragging) updateIrPosition(evt)
}
function updateIrPosition(evt: MouseEvent) {
  const area = evt.currentTarget as HTMLElement
  const rect = area.getBoundingClientRect()
  module1Fields.x = Math.round(Math.min(Math.max(evt.clientX - rect.left, 0), rect.width))
  module1Fields.y = Math.round(Math.min(Math.max(evt.clientY - rect.top, 0), rect.height))
  module1Fields.clicked = true
}

function onDragStart(obj: { src: string }, evt: DragEvent) {
  draggingSrc.value = obj.src
  const empty = document.createElement('canvas')
  empty.width = empty.height = 0
  evt.dataTransfer!.setDragImage(empty, 0, 0)
  evt.dataTransfer!.setData('text/plain', obj.src)
}
function onDragEnd() {
  draggingSrc.value = null
  dragPreview.value = null
}
function onSandboxDragOver(evt: DragEvent) {
  if (!draggingSrc.value) return
  const rect = (evt.currentTarget as HTMLElement).getBoundingClientRect()
  const rawX = evt.clientX - rect.left
  const rawY = evt.clientY - rect.top
  const { width, height } = getScaledSize(draggingSrc.value)
  dragPreview.value = {
    src: draggingSrc.value,
    x: Math.round(rawX - width / 2),
    y: Math.round(rawY - height / 2)
  }
}
function onSandboxDragLeave() {
  dragPreview.value = null
}
function onSandboxDrop(evt: DragEvent) {
  if (!draggingSrc.value) return
  const rect = (evt.currentTarget as HTMLElement).getBoundingClientRect()
  const rawX = evt.clientX - rect.left
  const rawY = evt.clientY - rect.top
  const { width, height } = getScaledSize(draggingSrc.value)
  const shape = draggingSrc.value.split('/').pop()!.replace('.png', '')
  const id = `${shape}-${placedObjects.length}-${Date.now()}`
  placedObjects.push({
    src: draggingSrc.value,
    x: Math.round(rawX - width / 2),
    y: Math.round(rawY - height / 2),
    id
  })
  draggingSrc.value = null
  dragPreview.value = null
}

function removeObjects() {
  placedObjects.forEach(o => removeObjectsBuf.push(o.id))
  placedObjects.splice(0)
  removeObjectsBuf.splice(0)
}

function getScaledSize(src: string) {
  const size = imageSizes[src] || { width: 50, height: 50 }
  return { width: size.width / scale, height: size.height / scale }
}

// Envoi payloads
function sendById(id: number) {
  if (id === 1) return sendModule1()
  if (id === 2) return sendModule2()
  if (id === 3) return sendModule3()
  if (id === 4) return sendModule4()
}

function sendModule1() {
  clients[1].setBuffer({
    x: module1Fields.x,
    y: module1Fields.y,
    diameter: module1Fields.diameter
  })
}
function sendModule2() {
  clients[2].setBuffer({
    rotX: module2Fields.rotX,
    rotY: module2Fields.rotY,
    rotZ: module2Fields.rotZ
  })
}
function sendModule3() {
  clients[3].setBuffer({
    uid1: module3Fields.uid1,
    uid2: module3Fields.uid2,
    uid3: module3Fields.uid3,
    current_set: module3Fields.current_set,
    button_pressed: module3Fields.button_pressed,
    timer: formattedTimer.value
  })
}
function sendModule4() {
  const newBgs = newBackgroundsBuf.map(b => ({
    id: b.id,
    type: 'background',
    shape: b.src.split('/').pop()!.replace('.png', ''),
    cx: 160, cy: 120,
    w: 305 / scale, h: 200 / scale,
    angle: 0.0, scale: 1.0
  }))
  const newObjs = placedObjects.map(o => {
    const size = imageSizes[o.src] || { width: 50, height: 50 }
    return {
      id: o.id,
      type: 'object',
      shape: o.src.split('/').pop()!.replace('.png', ''),
      cx: o.x + (size.width / scale) / 2,
      cy: o.y + (size.height / scale) / 2,
      w: size.width / scale,
      h: size.height / scale,
      angle: 0.0, scale: 1.0
    }
  })
  const payload = {
    newStrokes: [],
    removeStrokes: [],
    newObjects: newObjs,
    removeObjects: [...removeObjectsBuf],
    newBackgrounds: newBgs,
    removeBackgrounds: [...removeBackgroundsBuf],
    button: currentButton.value
  }
  clients[4]
    .setBuffer(payload)
    .then(() => {
      newBackgroundsBuf.splice(0)
      removeBackgroundsBuf.splice(0)
      newObjectsBuf.splice(0)
      removeObjectsBuf.splice(0)
    })
    .catch(err => console.error('Module4 send error:', err))
}

async function retrieveBuffer(mod: number) {
  try {
    const buf = await clients[mod].getBuffer()
    buffers[mod] = JSON.stringify(buf, null, 2)
  } catch (err) {
    buffers[mod] = `Erreur : ${err}`
  }
}

// Contrôle du timer global
function controlTimer(id: number, action: 'reset' | 'pause' | 'resume') {
  clients[id]
    .setBuffer({ timerControl: action })
    .catch(err => console.error(`Module${id} timerControl send error:`, err))
}

// Init des clients et listeners
onMounted(async () => {
  allItems.forEach(item => {
    const img = new Image()
    img.src = item.src
    img.onload = () => {
      imageSizes[item.src] = { width: img.naturalWidth, height: img.naturalHeight }
    }
  })

  moduleIds.forEach(id => {
    const client = useArtineo(id)
    clients[id] = client
    buffers[id] = ''

    client.onMessage(msg => {
      if (msg.action === 'get_buffer') {
        const b = msg.buffer as any
        buffers[id] = JSON.stringify(b, null, 2)
        // update local simulation fields
        if (id === 1) {
          module1Fields.x = b.x ?? module1Fields.x
          module1Fields.y = b.y ?? module1Fields.y
          module1Fields.diameter = b.diameter ?? module1Fields.diameter
          module1Fields.clicked = true
        }
        if (id === 2) {
          if (typeof b.rotX === 'number') module2Fields.rotX = b.rotX
          if (typeof b.rotY === 'number') module2Fields.rotY = b.rotY
          if (typeof b.rotZ === 'number') module2Fields.rotZ = b.rotZ
        }
        if (id === 3) {
          module3Fields.uid1 = b.uid1 ?? ''
          module3Fields.uid2 = b.uid2 ?? ''
          module3Fields.uid3 = b.uid3 ?? ''
          module3Fields.current_set = b.current_set ?? module3Fields.current_set
          module3Fields.button_pressed = b.button_pressed ?? false
          if (typeof b.timer === 'string') {
            const parts = b.timer.split(':').map(v => parseInt(v, 10))
            if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
              module3Fields.timer = parts[0] * 60 + parts[1]
            }
          }
        }
        // handle timerControl commands per module
        if (b.timerControl && typeof b.timerControl === 'string') {
          // each module’s composable must handle this via its own onMessage
        }
      }
    })
  })

  // fetch config module3
  try {
    const cfg = await clients[3].fetchConfig()
    module3Config.answers = cfg.answers || []
    module3Config.wanted_assignments = cfg.wanted_assignments || { lieux: [], couleurs: [], emotions: [] }
    module3Config.assignments = cfg.assignments || { lieux: {}, couleurs: {}, emotions: {} }
    module3Fields.current_set = 1
  } catch (e) {
    console.error('fetchConfig module 3 :', e)
  }

  // streaming watchers
  moduleIds.forEach(id => {
    watch(() => streaming[id], enabled => {
      if (enabled) {
        intervals[id] = window.setInterval(() => sendById(id), 100)
      } else {
        if (intervals[id] !== null) {
          clearInterval(intervals[id]!)
          intervals[id] = null
        }
      }
    })
  })
})

onBeforeUnmount(() => {
  Object.values(intervals).forEach(iv => iv !== null && clearInterval(iv))
})

onUnmounted(() => {
  Object.values(intervals).forEach(iv => iv !== null && clearInterval(iv))
})
</script>

<style scoped>
html, body, #__nuxt, .module-container {
  overflow: visible !important;
}

.simulation-dashboard {
  padding: 2rem;
  font-family: sans-serif;
  max-height: 100vh;
  overflow-y: auto;
}

.simulator-card {
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

/* MODULE 1 */
.module1-controls .ir-area-container {
  display: flex;
  align-items: center;
}

.ir-area {
  position: relative;
  width: 320px;
  height: 240px;
  background: #f0f0f0;
  border: 1px solid #333;
  cursor: crosshair;
}

.ir-marker {
  position: absolute;
  width: 12px;
  height: 12px;
  background: red;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
}

.ir-coords {
  margin-left: 1rem;
  font-family: monospace;
}

.slider-label {
  margin: 1rem 0;
  display: flex;
  align-items: center;
}

.slider-label input[type='range'] {
  margin: 0 0.5rem;
}

/* MODULE 2 */
.module2-controls label {
  display: flex;
  align-items: center;
  margin: 0.5rem 0;
}

.module2-controls input[type='range'] {
  margin-left: 0.5rem;
  flex: 1;
}

.module2-controls span {
  width: 60px;
  text-align: right;
  margin-left: 0.5rem;
  font-family: monospace;
}

/* MODULE 3, 4 General */
.controls {
  display: flex;
  flex-direction: column;
  margin-bottom: 1rem;
}

.button-row {
  margin-top: 0.5rem;
}

.button-row button {
  margin-right: 0.5rem;
}

.output {
  background: #f9f9f9;
  padding: 0.5rem;
  border-radius: 4px;
}

.output pre {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

/* Timer controls */
.timer-controls {
  margin: 0.5rem 0;
}

.timer-controls button {
  margin-right: 0.5rem;
}

/* MODULE 4 */
.background-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
}

.palette {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.remove-buttons {
  margin-bottom: 1rem;
}

.remove-buttons button {
  margin-right: 0.5rem;
}

.drag-preview {
  position: absolute;
  z-index: 2;
  opacity: 0.7;
  pointer-events: none;
  width: 50px;
  /* taille par défaut */
  height: 50px;
  /* taille par défaut */
}

.palette .draggable-item {
  cursor: grab;
  /* désactive la sélection de texte pour un drag plus fluide */
  user-select: none;
}

.palette .draggable-item:active {
  cursor: grabbing;
}

/* On empêche l'image d'intercepter le drag, pour que tout le bouton soit draggable */
.palette .draggable-item img {
  pointer-events: none;
}

.button-selector {
  margin-bottom: 0.5rem;
}

.button-selector button {
  margin-right: 0.5rem;
  padding: 0.3em 0.6em;
}

.button-selector button.active {
  background: #42b983;
  color: white;
}

/* overlay au-dessus du fond et sous les objets */
.sandbox-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.module4-container,
.sandbox,
.draggable-item {
  touch-action: none;
  overscroll-behavior: contain;
}


/* SWITCH TOGGLE */
.switch {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
  margin: 0.5rem 0;
  font-size: 0.9rem;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.switch .slider {
  position: relative;
  width: 40px;
  height: 20px;
  margin-left: 0.5rem;
  background-color: #ccc;
  border-radius: 34px;
  transition: background-color 0.2s;
}

.switch .slider::before {
  content: "";
  position: absolute;
  height: 16px;
  width: 16px;
  left: 2px;
  top: 2px;
  background-color: white;
  border-radius: 50%;
  transition: transform 0.2s;
}

.switch input:checked+.slider {
  background-color: #4caf50;
}

.switch input:checked+.slider::before {
  transform: translateX(20px);
}

.switch .slider.round {
  border-radius: 34px;
}

.switch .slider.round::before {
  border-radius: 50%;
}

/* MODULE 4 : sandbox & palette */
.module4-container {
  display: flex;
  align-items: flex-start;
  flex-direction: column;
  gap: 1rem;
}

.sandbox {
  position: relative;
  width: 305px;
  height: 200px;
  background: #f0f0f0;
  border: 1px solid #333;
  cursor: pointer;
}

.placed-object {
  position: absolute;
  z-index: 3;
  width: 50px;
  height: 50px;
  pointer-events: none;
}

.object-palette {
  display: flex;
  flex-direction: column;
  margin-left: 1rem;
}

.object-palette button {
  display: flex;
  align-items: center;
  margin-bottom: 0.5rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid #ccc;
  background: white;
  cursor: pointer;
}

.object-palette button.selected {
  border-color: #4caf50;
}

.object-icon,
.palette-icon {
  width: 40px;
  height: 40px;
  object-fit: contain;
  margin-right: 0.5rem;
}
</style>
