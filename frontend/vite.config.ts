import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Allow external connections (VS Code port forwarding)
    port: 5179,
    strictPort: true, // Fail if port is already in use
    // Sprint 101 Fix: Proxy API requests to backend
    // Sprint 112 Fix: Use Docker service name 'api' instead of 'localhost'
    // Inside Docker, 'localhost' refers to the container itself
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET || 'http://api:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
