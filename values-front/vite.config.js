import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  // 开发与预览都通过代理把 /api 转发到后端，前端只依赖同源 /api，无需处理跨域
  server: {
    proxy: { '/api': { target: 'http://localhost:8080', changeOrigin: true } },
  },
  preview: {
    proxy: { '/api': { target: 'http://localhost:8080', changeOrigin: true } },
  },
})
