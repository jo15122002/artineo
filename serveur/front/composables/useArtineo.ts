// front/composables/useArtineo.ts
import { useRuntimeConfig } from '#app'
import { ArtineoClient } from '~/utils/ArtineoClient'

const clients: Record<number, ArtineoClient> = {}

export function useArtineo(moduleId: number) {
  const { public: { apiUrl, wsUrl } } = useRuntimeConfig()

  // Si une instance existe déjà pour ce moduleId, on la réutilise
  if (!clients[moduleId]) {
    clients[moduleId] = new ArtineoClient(moduleId, apiUrl, wsUrl)
  }

  const client = clients[moduleId]

  // Expose les méthodes
  return {
    fetchConfig: () => client.fetchConfig(),
    setConfig:   (patch: any) => client.setConfig(patch),
    getBuffer:   () => client.getBuffer(),
    setBuffer:   (buf: any) => client.setBuffer(buf),
    onMessage:   (fn: (msg: any) => void) => client.onMessage(fn),
    close:       () => {
      client.close()
      delete clients[moduleId]  // supprime l’instance du cache
    },
  }
}
