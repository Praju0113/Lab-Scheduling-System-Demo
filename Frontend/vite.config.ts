import { defineConfig, loadEnv } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'

const projectRoot = new URL('.', import.meta.url).pathname
const srcPath = new URL('./src', import.meta.url).pathname

export default defineConfig(({ mode }: { mode: string }) => {
  const env = loadEnv(mode, projectRoot, '')
  const apiTarget = (env.VITE_API_BASE_URL || env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/api\/?$/i, '')

  return {
    plugins: [
      react(),
      tailwindcss(),
    ],
    resolve: {
      alias: {
        '@': srcPath,
      },
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/socket.io': {
          target: apiTarget,
          changeOrigin: true,
          ws: true,
        },
      },
    },
    assetsInclude: ['**/*.svg', '**/*.csv'],
  }
})
