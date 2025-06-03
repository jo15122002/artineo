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

export function useArtineo(moduleId: number) {
  // Si on est en SSR, on renvoie un stub silencieux pour éviter toute erreur d'import
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

  const nuxtApp = useNuxtApp()
  const factory = nuxtApp.$artineo as (id: number) => any

  if (typeof factory !== 'function') {
    // Si le plugin n'est pas injecté, on retourne également un stub
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

  // Le plugin artineo a été injecté, on l'utilise pour créer un client réel
  return factory(moduleId)
}
