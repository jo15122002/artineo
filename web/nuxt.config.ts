// nuxt.config.ts
import { defineNuxtConfig } from 'nuxt/config'
import viteTsconfigPaths from 'vite-tsconfig-paths'

export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: true },

  // 1️⃣ Dev server (npm run dev) écoute sur toutes les interfaces
  devServer: {
    host: '0.0.0.0',
    port: 3000
  },

  // 2️⃣ Modules officiels
  modules: [
    '@nuxt/eslint',
    '@nuxt/icon',
    '@nuxt/fonts'
  ],

  // 3️⃣ CSS global
  css: [
    '@/assets/css/style.css'
  ],

  // 4️⃣ Variables d'environnement exposées au client
  runtimeConfig: {
    public: {
      serverUrl: process.env.PUBLIC_SERVER_URL || 'localhost:3000'
    }
  },

  // 5️⃣ Head HTML
  app: {
    head: {
      title: 'My App',
      meta: [
        { name: 'description', content: 'My amazing Nuxt3 application' }
      ]
    }
  },

  // 6️⃣ Plugin Vite pour alias TS
  vite: {
    plugins: [
      viteTsconfigPaths()
    ]
  }
})