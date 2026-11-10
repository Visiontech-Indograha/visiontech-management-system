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
    build: {
      rollupOptions: {
        output: {
          // Vendor besar dipisah agar cache browser awet antar rilis.
          manualChunks(id: string) {
            if (!id.includes('node_modules')) return undefined
            if (/node_modules\/(react-leaflet|@react-leaflet|leaflet)\//.test(id)) return 'leaflet'
            if (/node_modules\/(react|react-dom|scheduler|react-router|react-router-dom)\//.test(id)) return 'vendor-react'
            if (/node_modules\/@tanstack\//.test(id)) return 'vendor-tanstack'
            if (/node_modules\/(zod|react-hook-form|@hookform)\//.test(id)) return 'vendor-form'
            if (/node_modules\/(radix-ui|@radix-ui)\//.test(id)) return 'vendor-radix'
            return undefined
          },
        },
      },
    },
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