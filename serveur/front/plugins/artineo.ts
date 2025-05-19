// plugins/artineo.ts
import { defineNuxtPlugin, useRuntimeConfig } from '#app'
import { ArtineoClient } from '~/utils/ArtineoClient'; // ← TS version

export default defineNuxtPlugin((nuxtApp) => {
  const { apiUrl, wsUrl } = useRuntimeConfig().public

  // Injecte la factory $artineo(moduleId: number)
  nuxtApp.provide('artineo', (moduleId: number) =>
    new ArtineoClient(moduleId, apiUrl, wsUrl)
  )
})
