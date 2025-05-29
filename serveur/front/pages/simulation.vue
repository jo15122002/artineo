<template>
  <div class="simulation-dashboard">
    <h1>Simulateur de modules</h1>
    <div
      v-for="mod in moduleIds"
      :key="mod"
      class="simulator-card"
    >
      <h2>Module {{ mod }}</h2>
      <div class="controls">
        <label>Payload JSON :</label>
        <textarea
          v-model="payloads[mod]"
          rows="6"
          placeholder='{"foo":"bar"}'
        ></textarea>
        <button @click="sendBuffer(mod)">Envoyer buffer</button>
        <button @click="retrieveBuffer(mod)">Récupérer buffer</button>
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

// — évite les `<…>` dans le parseur Vue, on cast plutôt en TS
const clients  = reactive({} as Record<number, ReturnType<typeof useArtineo>>)
const payloads = reactive({} as Record<number, string>)
const buffers  = reactive({} as Record<number, string>)

onMounted(() => {
  moduleIds.forEach(id => {
    const client = useArtineo(id)
    clients[id] = client
    payloads[id] = ''
    buffers[id]  = ''
    client.onMessage(msg => {
      if (msg.action === 'get_buffer') {
        buffers[id] = JSON.stringify(msg.buffer, null, 2)
      }
    })
  })
})

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
    buffers[mod] = `Erreur HTTP : ${err}`
  }
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
}
.controls textarea {
  font-family: monospace;
  margin-bottom: .5rem;
}
.controls button {
  margin-right: .5rem;
}
.output {
  background: #f9f9f9;
  padding: .5rem;
  border-radius: 4px;
  margin-top: 1rem;
}
.output pre {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
