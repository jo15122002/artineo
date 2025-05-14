<script setup lang="ts">
import { useRuntimeConfig } from '#app'
import { onBeforeUnmount, onMounted, reactive } from 'vue'
import type { BufferPayload } from '~/utils/ArtineoClient'

interface ModuleInfo {
  status: string
  buffer: BufferPayload | null
}

const { public: { apiUrl } } = useRuntimeConfig()

const modules = reactive<Record<string, ModuleInfo>>({})

/** Récupère l’état (alive/dead) via /hc */
async function fetchHealth() {
  try {
    const res = await fetch(`${apiUrl}/hc`)
    const json = await res.json() as { modules: Record<string, string> }
    console.log('[Dashboard] fetchHealth', json)
    // met à jour ou crée chaque module
    for (const [id, status] of Object.entries(json.modules)) {
      if (!modules[id]) modules[id] = { status: 'unknown', buffer: null }
      modules[id].status = status
    }
    // supprime ceux qui ont disparu
    for (const id of Object.keys(modules)) {
      if (!(id in json.modules)) delete modules[id]
    }
  } catch (e) {
    console.error('[Dashboard] fetchHealth error', e)
  }
}

/** Récupère la dernière donnée du buffer pour un module */
async function fetchBuffer(id: string) {
  try {
    const res = await fetch(`${apiUrl}/buffer?module=${id}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const json = await res.json() as { buffer: BufferPayload }
    modules[id].buffer = json.buffer
  } catch (e) {
    console.warn(`[Dashboard] fetchBuffer error (module ${id})`, e)
    modules[id].buffer = null
  }
}

let healthInterval: ReturnType<typeof setInterval>
let bufferInterval: ReturnType<typeof setInterval>

onMounted(() => {
  // passe initiale
  fetchHealth().then(() => {
    Object.keys(modules).forEach(fetchBuffer)
  })

  // refresh état toutes les 5s
  healthInterval = setInterval(fetchHealth, 5000)
  // refresh buffer toutes les 5s
  bufferInterval = setInterval(() => {
    Object.keys(modules).forEach(fetchBuffer)
  }, 5000)
})

onBeforeUnmount(() => {
  clearInterval(healthInterval)
  clearInterval(bufferInterval)
})
</script>

<template>
  <div class="dashboard">
    <h1>Dashboard des modules</h1>
    <p v-if="!Object.keys(modules).length">Aucun module détecté pour le moment.</p>
    <div
      v-for="(info, id) in modules"
      :key="id"
      class="module-card"
    >
      <h2>Module {{ id }}</h2>
      <p>
        Statut :
        <strong
          :class="{
            connected:    info.status === 'alive',
            disconnected: info.status !== 'alive'
          }"
        >
          {{ info.status === 'alive' ? 'Connecté' : 'Déconnecté' }}
        </strong>
      </p>
      <div class="buffer">
        <h3>Dernière donnée du buffer</h3>
        <pre v-if="info.buffer">{{ info.buffer }}</pre>
        <p v-else>Aucune donnée</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 1rem;
  font-family: Arial, sans-serif;
}
.module-card {
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 1rem;
  margin-bottom: 1rem;
}
.module-card h2 {
  margin: 0 0 0.5rem;
}
.connected {
  color: green;
}
.disconnected {
  color: red;
}
.buffer {
  background: #f9f9f9;
  padding: 0.5rem;
  border-radius: 4px;
  margin-top: 0.5rem;
}
.buffer pre {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}
</style>
