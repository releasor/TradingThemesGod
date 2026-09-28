import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        // 固定 IPv4：Windows 上 localhost 常解析到 ::1，而后端只绑 127.0.0.1 → 502
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // 图谱/资料刷新含抓取与模型调用，常超过默认 2 分钟
        timeout: 600_000,
        proxyTimeout: 600_000,
        configure: (proxy) => {
          // Prompt 优化 SSE：禁止代理侧缓冲，否则会整段到达才渲染
          proxy.on('proxyRes', (proxyRes) => {
            const ct = String(proxyRes.headers['content-type'] || '')
            if (!ct.includes('text/event-stream')) return
            proxyRes.headers['cache-control'] = 'no-cache, no-transform'
            proxyRes.headers['x-accel-buffering'] = 'no'
            delete proxyRes.headers['content-length']
          })
        },
      },
    },
  },
})
