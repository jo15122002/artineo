// File: serveur/front/plugins/artineo.ts
import { defineNuxtPlugin, useRuntimeConfig } from '#app'
import { ArtineoClient } from '~/utils/ArtineoClient'

export default defineNuxtPlugin((nuxtApp) => {
  const { apiUrl, wsUrl } = useRuntimeConfig().public
  // Map pour conserver une instance par moduleId
  const mapClients: Record<number, ArtineoClient> = {}

  nuxtApp.provide('artineo', (moduleId: number) => {
    if (mapClients[moduleId]) {
      return mapClients[moduleId]
    }
    const client = new ArtineoClient(moduleId, apiUrl, wsUrl)
    mapClients[moduleId] = client
    return client
  })
})
