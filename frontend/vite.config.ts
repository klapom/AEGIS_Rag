import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Allow external connections (VS Code port forwarding)
    port: 5179,
    strictPort: true, // Fail if port is already in use
  },
})
