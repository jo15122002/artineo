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
              :style="{ left: module1Fields.x + 'px', top: module1Fields.y + 'px' }"></div>
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
          <input type="range" v-model.number="module2Fields.rotX" :min="-6.28" :max="6.28" :step="0.01" />
          <span>{{ module2Fields.rotX.toFixed(2) }}</span>
        </label>
        <label>
          rotY :
          <input type="range" v-model.number="module2Fields.rotY" :min="-6.28" :max="6.28" :step="0.01" />
          <span>{{ module2Fields.rotY.toFixed(2) }}</span>
        </label>
        <label>
          rotZ :
          <input type="range" v-model.number="module2Fields.rotZ" :min="-6.28" :max="6.28" :step="0.01" />
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
              <button v-for="obj in objectItems" :key="obj.src" class="draggable-item" draggable="true"
                @dragstart="onDragStart(obj, $event)" @dragend="onDragEnd">
                <img :src="obj.src" class="palette-icon" draggable="false" alt="" />
                {{ obj.name }}
              </button>
            </div>
          </div>

          <!-- Sandbox -->
          <div class="sandbox" @dragover.prevent="onSandboxDragOver" @dragleave="onSandboxDragLeave"
            @drop.prevent="onSandboxDrop">
            <!-- Background permanent -->
            <img v-if="currentBackground" :src="currentBackground.src" class="background-image" />

            <img v-for="obj in placedObjects" :key="obj.id" :src="obj.src" class="placed-object" :style="{
              left: obj.x + 'px',
              top: obj.y + 'px',
              width: (imageSizes[obj.src]?.width || 50) / scale + 'px',
              height: (imageSizes[obj.src]?.height || 50) / scale + 'px'
            }" />

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

      <!-- Boutons d'action -->
      <div class="button-row">
        <button @click="mod === 1
          ? sendModule1()
          : mod === 2
            ? sendModule2()
            : mod === 3
              ? sendModule3()
              : sendModule4()">
          Envoyer buffer
        </button>
        <button @click="retrieveBuffer(mod)">
          Récupérer buffer
        </button>
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
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useArtineo } from '~/composables/useArtineo'

const moduleIds = [1, 2, 3, 4]
const clients = reactive<Record<number, ReturnType<typeof useArtineo>>>({})
const payloads = reactive<Record<number, string>>({ 2: '{}', 4: '{}' })
const buffers = reactive<Record<number, string>>({ 2: '{}', 4: '{}' })

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
  button_pressed: false
})
const module3Config = reactive<{
  answers: any[]
  wanted_assignments: { lieux: string[]; couleurs: string[]; emotions: string[] }
  assignments: {
    lieux: Record<string, string>
    couleurs: Record<string, string>
    emotions: Record<string, string>
  }
}>({
  answers: [],
  wanted_assignments: { lieux: [], couleurs: [], emotions: [] },
  assignments: { lieux: {}, couleurs: {}, emotions: {} }
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
// Sépare les backgrounds et les autres objets
const backgrounds = computed(() =>
  allItems.filter(i => i.name.startsWith('landscape_'))
)
const objectItems = computed(() =>
  allItems.filter(i => !i.name.startsWith('landscape_'))
)

const imageSizes = reactive<Record<string, { width: number; height: number }>>({})

// État
const currentBackground = ref<{ src: string; id: string } | null>(null)
const selectedObject = ref<string | null>(null)
const placedObjects = reactive<Array<{ src: string; x: number; y: number; id: string }>>([])

const draggingSrc = ref<string | null>(null)
const dragPreview = ref<{ src: string; x: number; y: number } | null>(null)
const scale = 16 // échelle pour le module 4

// Buffers réfléchis
const newBackgroundsBuf = reactive<{ src: string; id: string }[]>([])
const removeBackgroundsBuf = reactive<string[]>([])
const newObjectsBuf = reactive<{ src: string; x: number; y: number; id: string }[]>([])
const removeObjectsBuf = reactive<string[]>([])

function getScaledSize(src: string) {
  const size = imageSizes[src] || { width: 50, height: 50 }
  return {
    width: size.width / scale,
    height: size.height / scale
  }
}

// --- Fonctions de sélection / placement ---
function setBackground(bg: { src: string }) {
  // si un fond était déjà posé, on planifie sa suppression
  if (currentBackground.value) {
    removeBackgroundsBuf.push(currentBackground.value.id)
    // et on nettoie l’entrée pending au cas où
    const idx = newBackgroundsBuf.findIndex(b => b.id === currentBackground.value!.id)
    if (idx >= 0) newBackgroundsBuf.splice(idx, 1)
  }
  // nouveau fond
  const id = `background-${Date.now()}`
  currentBackground.value = { src: bg.src, id }
  newBackgroundsBuf.splice(0) // on ne veut qu’un seul fond pending à la fois
  newBackgroundsBuf.push({ src: bg.src, id })
}

function onDragStart(obj: { src: string }, evt: DragEvent) {
  draggingSrc.value = obj.src

  // 1) créer un canvas vide pour masquer le ghost-browser
  const empty = document.createElement('canvas')
  empty.width = empty.height = 0
  evt.dataTransfer!.setDragImage(empty, 0, 0)

  // (optionnel) définir un mime-type pour compatibilité
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

// Choix d'un objet à placer
function selectObject(obj: { src: string }) {
  selectedObject.value = obj.src
}

function onSandboxClick(evt: MouseEvent) {
  if (!selectedObject.value) return
  const rect = (evt.currentTarget as HTMLElement).getBoundingClientRect()
  const x = Math.round(evt.clientX - rect.left)
  const y = Math.round(evt.clientY - rect.top)
  const shape = selectedObject.value.split('/').pop()!.replace('.png', '')
  const id = `${shape}-${placedObjects.length}-${Date.now()}`
  placedObjects.push({ src: selectedObject.value, x, y, id })
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

function removeObjects() {
  // planifier la suppression
  placedObjects.forEach(o => removeObjectsBuf.push(o.id))
  // vider l’affichage et le nouveau buffer
  placedObjects.splice(0)
  newObjectsBuf.splice(0)
}

function removeAll() {
  removeBackground()
  removeObjects()
}

// Streaming toggles & timers
const streaming = reactive<Record<number, boolean>>({
  1: false,
  2: false,
  3: false,
  4: false
})
const intervals = reactive<Record<number, number | null>>({
  1: null,
  2: null,
  3: null,
  4: null
})

// Helper: envoie selon l'ID du module
function sendById(id: number) {
  if (id === 1) return sendModule1()
  if (id === 2) return sendModule2()
  if (id === 3) return sendModule3()
  if (id === 4) return sendModule4()
}

// MODULE 4 : envoyez les objets placés structurés pour use4kinect
function sendModule4() {
  const scale = 16

  // on construit le payload à partir des buffers
  const newBackgrounds = newBackgroundsBuf.map(b => ({
    id: b.id,
    type: 'background',
    shape: b.src.split('/').pop()!.replace('.png', ''),
    cx: 160, cy: 120,
    w: 320 / scale, h: 240 / scale,
    angle: 0.0,
    scale: 1.0
  }))
  const newObjects = placedObjects.map(o => {
    const size = imageSizes[o.src] || { width: 50, height: 50 }
    const w = size.width  / scale
    const h = size.height / scale
    return {
      id: o.id,
      type: 'object',
      shape: o.src.split('/').pop()!.replace('.png', ''),
      // on envoie le centre, pas le coin
      cx: o.x + w / 2,
      cy: o.y + h / 2,
      w,
      h,
      angle: 0.0,
      scale: 1.0
    }
  })
  const payload = {
    newStrokes: [],
    removeStrokes: [],
    newObjects,
    removeObjects: [...removeObjectsBuf],
    newBackgrounds,
    removeBackgrounds: [...removeBackgroundsBuf]
  }

  clients[4]
    .setBuffer(payload)
    .then(() => {
      // on vide les buffers qui ont été envoyés
      newBackgroundsBuf.splice(0)
      removeBackgroundsBuf.splice(0)
      newObjectsBuf.splice(0)
      removeObjectsBuf.splice(0)
    })
    .catch(err => console.error('Module4 send error:', err))
}

// Fonctions Modules 1 à 3
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
    button_pressed: module3Fields.button_pressed
  })
}

// Fallback JSON send (non utilisé pour mod 4)
function sendBuffer(mod: number) {
  try {
    const raw = payloads[mod].trim()
    const data = raw ? JSON.parse(raw) : {}
    clients[mod].setBuffer(data)
  } catch (err) {
    alert(`JSON invalide : ${err}`)
  }
}

async function retrieveBuffer(mod: number) {
  try {
    const buf = await clients[mod].getBuffer()
    buffers[mod] = JSON.stringify(buf, null, 2)
  } catch (err) {
    buffers[mod] = `Erreur : ${err}`
  }
}

// Gestion zone IR (module 1)
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
  const x = Math.round(evt.clientX - rect.left)
  const y = Math.round(evt.clientY - rect.top)
  module1Fields.x = Math.min(Math.max(x, 0), rect.width)
  module1Fields.y = Math.min(Math.max(y, 0), rect.height)
  module1Fields.clicked = true
}

onMounted(async () => {

  allItems.forEach(item => {
    const img = new Image()
    img.src = item.src
    img.onload = () => {
      imageSizes[item.src] = {
        width: img.naturalWidth,
        height: img.naturalHeight
      }
    }
  })

  moduleIds.forEach(id => {
    const client = useArtineo(id)
    clients[id] = client
    payloads[id] = id === 2 || id === 4 ? '{}' : ''
    buffers[id] = ''

    client.onMessage(msg => {
      if (msg.action === 'get_buffer') {
        buffers[id] = JSON.stringify(msg.buffer, null, 2)
        const b = msg.buffer as any
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
        }
      }
    })
  })

  try {
    const cfg = await clients[3].fetchConfig()
    module3Config.answers = cfg.answers || []
    module3Config.wanted_assignments = cfg.wanted_assignments || {
      lieux: [],
      couleurs: [],
      emotions: []
    }
    module3Config.assignments = cfg.assignments || {
      lieux: {},
      couleurs: {},
      emotions: {}
    }
    module3Fields.current_set = 1
  } catch (e) {
    console.error('fetchConfig module 3 :', e)
  }

  // Watchers pour le toggle streaming
  moduleIds.forEach(id => {
    watch(
      () => streaming[id],
      enabled => {
        if (enabled) {
          intervals[id] = window.setInterval(() => sendById(id), 100)
        } else {
          if (intervals[id] !== null) {
            clearInterval(intervals[id]!)
            intervals[id] = null
          }
        }
      }
    )
  })
})

onUnmounted(() => {
  moduleIds.forEach(id => {
    if (intervals[id] !== null) {
      clearInterval(intervals[id]!)
      intervals[id] = null
    }
  })
})
</script>

<style scoped>
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

/* MODULE 3, 4 Général */
.controls {
  display: flex;
  flex-direction: column;
  margin-bottom: 1rem;
}

.controls textarea {
  margin: 0.5rem 0;
  font-family: monospace;
}

.controls select,
.controls input[type='checkbox'] {
  margin-left: 0.5rem;
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

/* MODULE 4 : Sandbox & Palette */
.background-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
}

.placed-object {
  position: absolute;
  z-index: 1;
}

.palette {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.palette button.selected {
  outline: 2px solid #42b983;
}

.remove-buttons {
  margin-bottom: 1rem;
}

.remove-buttons button {
  margin-right: 0.5rem;
}

.background-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
}

.placed-object {
  position: absolute;
  z-index: 1;
}

.palette {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.palette button.selected {
  outline: 2px solid #42b983;
}

.sandbox {
  position: relative;
  width: 305px;
  height: 200px;
  border: 1px solid #ccc;
  overflow: hidden;
}

.background-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
}

.placed-object {
  position: absolute;
  z-index: 1;
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

.palette .draggable-item img {
  pointer-events: none;
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
  width: 320px;
  height: 240px;
  background: #f0f0f0;
  border: 1px solid #333;
  cursor: pointer;
}

.placed-object {
  position: absolute;
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
