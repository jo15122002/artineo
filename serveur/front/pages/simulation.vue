<template>
  <div class="simulation-dashboard">
    <h1>Simulateur de modules</h1>
    <div
      v-for="mod in moduleIds"
      :key="mod"
      class="simulator-card"
    >
      <h2>Module {{ mod }}</h2>

      <!-- MODULE 3 : listes déroulantes dynamiques -->
      <div v-if="mod === 3" class="controls">
        <label>
          Lieu :
          <select v-model="module3Fields.uid1">
            <option value="">-- Choisir un lieu --</option>
            <option
              v-for="label in module3Config.wanted_assignments.lieux"
              :key="label"
              :value="module3Config.assignments.lieux[label]"
            >
              {{ label }}
            </option>
          </select>
        </label>

        <label>
          Couleur :
          <select v-model="module3Fields.uid2">
            <option value="">-- Choisir une couleur --</option>
            <option
              v-for="label in module3Config.wanted_assignments.couleurs"
              :key="label"
              :value="module3Config.assignments.couleurs[label]"
            >
              {{ label }}
            </option>
          </select>
        </label>

        <label>
          Émotion :
          <select v-model="module3Fields.uid3">
            <option value="">-- Choisir une émotion --</option>
            <option
              v-for="label in module3Config.wanted_assignments.emotions"
              :key="label"
              :value="module3Config.assignments.emotions[label]"
            >
              {{ label }}
            </option>
          </select>
        </label>

        <label>
          Jeu courant :
          <select v-model.number="module3Fields.current_set">
            <option
              v-for="(ans, i) in module3Config.answers"
              :key="i"
              :value="i+1"
            >
              Set {{ i+1 }}
            </option>
          </select>
        </label>

        <label>
          Bouton pressé :
          <input
            type="checkbox"
            v-model="module3Fields.button_pressed"
          />
        </label>

        <div class="button-row">
          <button @click="sendModule3()">Envoyer buffer</button>
          <button @click="retrieveBuffer(3)">Récupérer buffer</button>
        </div>
      </div>

      <!-- AUTRES MODULES : JSON libre -->
      <div v-else class="controls">
        <label>Payload JSON :</label>
        <textarea
          v-model="payloads[mod]"
          rows="6"
          placeholder='{"foo":"bar"}'
        ></textarea>
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

// Liste de tous les modules
const moduleIds = [1, 2, 3, 4]

// Clients WS et zones de stockage génériques
const clients  = reactive({} as Record<number, ReturnType<typeof useArtineo>>)
const payloads = reactive({} as Record<number, string>)
const buffers  = reactive({} as Record<number, string>)

// Champs dédiés au module 3
const module3Fields = reactive({
  uid1: '',
  uid2: '',
  uid3: '',
  current_set: 1,
  button_pressed: false
})

// Config du module 3 (récupérée via fetchConfig)
const module3Config = reactive<{
  answers: any[],
  wanted_assignments: { lieux: string[]; couleurs: string[]; emotions: string[] },
  assignments: { lieux: Record<string,string>; couleurs: Record<string,string>; emotions: Record<string,string> }
}>({
  answers: [],
  wanted_assignments: { lieux: [], couleurs: [], emotions: [] },
  assignments: { lieux: {}, couleurs: {}, emotions: {} }
})

onMounted(async () => {
  moduleIds.forEach(id => {
    const client = useArtineo(id)
    clients[id] = client
    payloads[id] = ''
    buffers[id]  = ''

    client.onMessage(msg => {
      if (msg.action === 'get_buffer') {
        buffers[id] = JSON.stringify(msg.buffer, null, 2)

        // si c'est pour le module 3, on hydrate aussi les champs
        if (id === 3) {
          const b = msg.buffer as any
          module3Fields.uid1          = b.uid1          ?? ''
          module3Fields.uid2          = b.uid2          ?? ''
          module3Fields.uid3          = b.uid3          ?? ''
          module3Fields.current_set   = b.current_set   ?? module3Fields.current_set
          module3Fields.button_pressed= b.button_pressed?? false
        }
      }
    })
  })

  // --- récupérer la config du module 3 pour construire nos selects ---
  try {
    const cfg = await clients[3].fetchConfig()
    module3Config.answers            = cfg.answers            || []
    module3Config.wanted_assignments = cfg.wanted_assignments || { lieux: [], couleurs: [], emotions: [] }
    module3Config.assignments        = cfg.assignments        || { lieux: {}, couleurs: {}, emotions: {} }
    // s'assurer qu'on a au moins un set choisi
    module3Fields.current_set = 1
  } catch (e) {
    console.error("Erreur fetchConfig module 3 :", e)
  }
})

function sendBuffer(mod: number) {
  try {
    const raw  = payloads[mod].trim()
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
    buffers[mod] = `Erreur HTTP : ${err}`
  }
}

function sendModule3() {
  const data = {
    uid1:           module3Fields.uid1,
    uid2:           module3Fields.uid2,
    uid3:           module3Fields.uid3,
    current_set:    module3Fields.current_set,
    button_pressed: module3Fields.button_pressed
  }
  clients[3].setBuffer(data)
}
</script>

<style scoped>
.simulation-dashboard {
  padding: 2rem;
  font-family: sans-serif;
}
.simulator-card {
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}
.controls {
  display: flex;
  flex-direction: column;
  margin-bottom: 1rem;
}
.controls label {
  margin: .25rem 0;
}
.controls input,
.controls select,
.controls textarea {
  font-family: monospace;
  margin-left: .5rem;
  padding: .25rem;
}
.button-row {
  margin-top: .5rem;
}
.button-row button {
  margin-right: .5rem;
}
.output {
  background: #f9f9f9;
  padding: .5rem;
  border-radius: 4px;
}
.output pre {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}
</style>
