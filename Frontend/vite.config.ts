import { defineConfig, loadEnv } from 'vite'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'

const projectRoot = new URL('.', import.meta.url).pathname
const repoRoot = new URL('../', import.meta.url).pathname
const srcPath = new URL('./src', import.meta.url).pathname

const getRequiredEnv = (env: Record<string, string>, name: string) => {
  const value = env[name]?.trim()
  if (value) {
    return value
  }
  throw new Error(`Missing required environment variable: ${name}`)
}

export default defineConfig(({ mode }: { mode: string }) => {
  const env = loadEnv(mode, repoRoot, '')
  const apiTarget = (env.VITE_API_BASE_URL || env.VITE_API_URL || getRequiredEnv(env, 'VITE_API_BASE_URL')).replace(/\/api\/?$/i, '')
  const frontendPort = Number.parseInt(getRequiredEnv(env, 'FRONTEND_PORT'), 10)

  return {
    envDir: repoRoot,
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
      port: frontendPort,
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
