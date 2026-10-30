import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'
import { readFileSync } from 'node:fs'

// Versi aplikasi = package.json (disinkronkan dari VERSION oleh scripts/versi.sh).
const APP_VERSION: string = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf-8')).version

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react(), tailwindcss()],
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    define: { __APP_VERSION__: JSON.stringify(APP_VERSION) },
    server: {
      port: 5173,
      fs: {
        allow: ['../..'],
      },
      proxy: {
        '/api': {
          target: env.DEV_API_PROXY_TARGET || 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})