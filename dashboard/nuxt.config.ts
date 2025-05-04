// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: { enabled: true },
  runtimeConfig: {
    public: {
      apiUrl: process.env.ARTINEO_HOST || '192.168.0.180',
      apiPort: process.env.ARTINEO_PORT || '8000',
    },
  }
})
