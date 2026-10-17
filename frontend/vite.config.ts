import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backend = env.VITE_DEV_BACKEND ?? 'http://127.0.0.1:8000'

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { '@': path.resolve(import.meta.dirname, './src') },
    },
    server: {
      // In dev the UI calls /api on its own origin and Vite forwards it to the local backend.
      proxy: {
        '/api': { target: backend, changeOrigin: true },
        '/health': { target: backend, changeOrigin: true },
        '/openapi.json': { target: backend, changeOrigin: true },
      },
    },
  }
})
