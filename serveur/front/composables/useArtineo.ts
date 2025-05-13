// front/composables/useArtineo.ts
import { useRuntimeConfig } from '#app'
import { ArtineoClient } from '~/utils/ArtineoClient'

export function useArtineo(moduleId: number) {
  const { public: { apiUrl, wsUrl } } = useRuntimeConfig()
  const client = new ArtineoClient(moduleId, apiUrl, wsUrl)

  // Expose les méthodes
  return {
    fetchConfig: () => client.fetchConfig(),
    setConfig:   (patch: any) => client.setConfig(patch),
    getBuffer:   () => client.getBuffer(),
    setBuffer:   (buf: any) => client.setBuffer(buf),
    onMessage:   (fn: (msg: any) => void) => client.onMessage(fn),
    close:       () => client.close(),
  }
}