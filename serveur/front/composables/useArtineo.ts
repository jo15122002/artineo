// File: serveur/front/composables/useArtineo.ts
import { useNuxtApp } from '#app'

/** Interface minimale pour un client Artineo côté SSR */
interface ArtineoStub {
  fetchConfig: () => Promise<any>
  setConfig: (patch: any) => Promise<any>
  getBuffer: () => Promise<any>
  setBuffer: (buf: any) => void
  onMessage: (fn: (msg: any) => void) => void
  close: () => void
}

/** Cache des instances ArtineoClient par moduleId */
const clientCache = new Map<number, any>()

export function useArtineo(moduleId: number) {
  // En SSR, on retourne un stub neutre
  if (!process.client) {
    const noop = () => {}
    const stub: ArtineoStub = {
      fetchConfig: async () => ({}),
      setConfig: async () => ({}),
      getBuffer: async () => ({}),
      setBuffer: () => {},
      onMessage: noop,
      close: noop,
    }
    return stub
  }

  // Si on a déjà créé le client pour ce moduleId, on le réutilise
  if (clientCache.has(moduleId)) {
    return clientCache.get(moduleId)
  }

  const nuxtApp = useNuxtApp()
  const factory = nuxtApp.$artineo as (id: number) => any

  if (typeof factory !== 'function') {
    // Si le plugin n'est pas injecté, on renvoie un stub
    const noop = () => {}
    const stub: ArtineoStub = {
      fetchConfig: async () => ({}),
      setConfig: async () => ({}),
      getBuffer: async () => ({}),
      setBuffer: () => {},
      onMessage: noop,
      close: noop,
    }
    clientCache.set(moduleId, stub)
    return stub
  }

  // On crée une nouvelle instance ArtineoClient pour ce moduleId
  const client = factory(moduleId)
  clientCache.set(moduleId, client)
  return client
}
