// https://nuxt.com/docs/api/configuration/nuxt-config

import { defineNuxtConfig } from 'nuxt/config'
import viteTsconfigPaths from 'vite-tsconfig-paths'

export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: true },
  modules: ['@nuxt/eslint', '@nuxt/icon', '@nuxt/fonts'],
  css: ['@/assets/css/style.css'],
  app: {
    head: {
        title: 'My App',
        meta: [
            { name: 'description', content: 'My amazing Nuxt3 application' }
        ]
    }
  },
  vite: {
    plugins: [
      viteTsconfigPaths()
    ]
  }
})