// nuxt.config.ts
import { defineNuxtConfig } from 'nuxt/config'

export default defineNuxtConfig({
  vite: {
    assetsInclude: ['**/*.woff2']
  },
  runtimeConfig: {
    public: {
      wsUrl: 'ws://' + process.env.IP,
      apiUrl: 'http://' + process.env.IP
    }
  }
})