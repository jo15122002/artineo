// nuxt.config.ts
import { defineNuxtConfig } from 'nuxt/config'

export default defineNuxtConfig({
  vite: {
    assetsInclude: ['**/*.woff2']
  },
  runtimeConfig: {
    public: {
      apiBase: process.env.API_BASE || 'http://127.0.0.1:8000'
    }
  }
})