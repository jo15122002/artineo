// plugins/artineo.client.ts
import { defineNuxtPlugin } from '#app'
import { ArtineoClient } from '~/lib/artineoClient'

export default defineNuxtPlugin((nuxtApp) => {
  const { apiUrl, wsUrl } = useRuntimeConfig().public

  // on fournit une factory : $artineo(moduleId?)
  return {
    provide: {
      artineo: (moduleId?: string) =>
        new ArtineoClient({ moduleId, apiUrl, wsUrl }),
    },
  }
})
