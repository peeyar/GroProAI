import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Backend location is env-driven (12-factor): GROPRO_API overrides the default.
const apiTarget = process.env.GROPRO_API ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': apiTarget,
    },
  },
})
