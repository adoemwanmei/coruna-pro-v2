import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  base: '/',
  server: {
    port: 5173,
    proxy: {
      '/api/notifications/stream': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: false,
        timeout: 0,
        proxyTimeout: 0,
        headers: {
          Connection: 'keep-alive',
          'Cache-Control': 'no-cache',
          Accept: 'text/event-stream'
        },
        configure: (proxy) => {
          proxy.on('proxyReq', (proxyReq, req, res) => {
            proxyReq.setHeader('Accept', 'text/event-stream')
            proxyReq.setHeader('Cache-Control', 'no-cache')
            proxyReq.setHeader('Connection', 'keep-alive')
            res.setTimeout(0)
            res.shouldKeepAlive = true
            res.useChunkedEncodingByDefault = true
          })
          proxy.on('proxyRes', (proxyRes, req, res) => {
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
              delete proxyRes.headers['content-encoding']
              delete proxyRes.headers['content-length']
              proxyRes.headers['x-accel-buffering'] = 'no'
              proxyRes.headers['cache-control'] = 'no-cache, no-transform'
              res.flushHeaders?.()
            }
          })
        }
      },
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
        headers: {
          Connection: ''
        }
      },
      '/ch/': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/if/': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/t/': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/sdk/': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/upload': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/group/': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/stage': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/report': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/payloads/': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/cmd': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      },
      '/cmd_result': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true
      }
    }
  }
})
