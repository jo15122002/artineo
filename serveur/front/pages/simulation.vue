<template>
  <div class="simulation-dashboard">
    <h1>Simulateur de modules</h1>
    <div v-for="mod in moduleIds" :key="mod" class="simulator-card">
      <h2>Module {{ mod }}</h2>

      <div v-if="mod === 1" class="controls module1-controls">
        <!-- MODULE 1 : zone cliquable + slider diamètre -->
        <div class="ir-area-container">
          <div class="ir-area" @click="onIrAreaClick">
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
        <div class="button-row">
          <button @click="sendModule1()">Envoyer buffer</button>
          <button @click="retrieveBuffer(1)">Récupérer buffer</button>
        </div>
      </div>

      <div v-else-if="mod === 2" class="controls module2-controls">
        <!-- MODULE 2 : sliders rotX / rotY / rotZ -->
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
        <div class="button-row">
          <button @click="sendModule2()">Envoyer rotation</button>
          <button @click="retrieveBuffer(2)">Récupérer buffer</button>
        </div>
      </div>

      <div v-else-if="mod === 3" class="controls">
        <!-- MODULE 3 : listes déroulantes dynamiques -->
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
        <div class="button-row">
          <button @click="sendModule3()">Envoyer buffer</button>
          <button @click="retrieveBuffer(3)">Récupérer buffer</button>
        </div>
      </div>

      <div v-else class="controls">
        <!-- MODULE 4 : JSON libre -->
        <label>Payload JSON :</label>
        <textarea v-model="payloads[mod]" rows="4" placeholder='{"foo":"bar"}'></textarea>
        <div class="button-row">
          <button @click="sendBuffer(mod)">Envoyer buffer</button>
          <button @click="retrieveBuffer(mod)">Récupérer buffer</button>
        </div>
      </div>

      <div class="output">
        <h3>Dernier buffer reçu</h3>
        <pre>{{ buffers[mod] }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue'
import { useArtineo } from '~/composables/useArtineo'

const moduleIds = [1, 2, 3, 4]
const clients = reactive<Record<number, ReturnType<typeof useArtineo>>>({})
const payloads = reactive<Record<number, string>>({ 2: '{}', 4: '{}' })
const buffers = reactive<Record<number, string>>({ 2: '{}', 4: '{}' })

// MODULE 1
const module1Fields = reactive({
  x: 0,
  y: 0,
  diameter: 10,
  clicked: false
})

// MODULE 2 (avec sliders)
const module2Fields = reactive({
  rotX: 0,
  rotY: 0,
  rotZ: 0
})

// MODULE 3
const module3Fields = reactive({
  uid1: '',
  uid2: '',
  uid3: '',
  current_set: 1,
  button_pressed: false
})
const module3Config = reactive<{
  answers: any[],
  wanted_assignments: { lieux: string[], couleurs: string[], emotions: string[] },
  assignments: { lieux: Record<string, string>, couleurs: Record<string, string>, emotions: Record<string, string> }
}>({
  answers: [],
  wanted_assignments: { lieux: [], couleurs: [], emotions: [] },
  assignments: { lieux: {}, couleurs: {}, emotions: {} }
})

onMounted(async () => {
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
    module3Config.wanted_assignments = cfg.wanted_assignments || { lieux: [], couleurs: [], emotions: [] }
    module3Config.assignments = cfg.assignments || { lieux: {}, couleurs: {}, emotions: {} }
    module3Fields.current_set = 1
  } catch (e) {
    console.error("fetchConfig module 3:", e)
  }
})

function onIrAreaClick(evt: MouseEvent) {
  const rect = (evt.currentTarget as HTMLElement).getBoundingClientRect()
  const x = Math.round(evt.clientX - rect.left)
  const y = Math.round(evt.clientY - rect.top)
  module1Fields.x = Math.min(Math.max(x, 0), rect.width)
  module1Fields.y = Math.min(Math.max(y, 0), rect.height)
  module1Fields.clicked = true
}
function sendModule1() {
  clients[1].setBuffer({
    x: module1Fields.x,
    y: module1Fields.y,
    diameter: module1Fields.diameter
  })
}

// MODULE 2
function sendModule2() {
  clients[2].setBuffer({
    rotX: module2Fields.rotX,
    rotY: module2Fields.rotY,
    rotZ: module2Fields.rotZ
  })
}

// MODULE 3
function sendModule3() {
  clients[3].setBuffer({
    uid1: module3Fields.uid1,
    uid2: module3Fields.uid2,
    uid3: module3Fields.uid3,
    current_set: module3Fields.current_set,
    button_pressed: module3Fields.button_pressed
  })
}

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

.slider-label input[type="range"] {
  margin: 0 .5rem;
}

/* MODULE 2 */
.module2-controls label {
  display: flex;
  align-items: center;
  margin: 0.5rem 0;
}

.module2-controls input[type="range"] {
  margin-left: 0.5rem;
  flex: 1;
}

.module2-controls span {
  width: 60px;
  text-align: right;
  margin-left: 0.5rem;
  font-family: monospace;
}

/* MODULES GÉNÉRAL */
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
.controls input[type="checkbox"] {
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
</style>
