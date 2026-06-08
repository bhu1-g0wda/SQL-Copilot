import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Split React into its own chunk — cached separately by browsers
          react: ['react', 'react-dom'],
          // Split the large syntax-highlighter library — lazy-loaded on first result
          'syntax-highlighter': ['react-syntax-highlighter'],
        },
      },
    },
    // Raise the warning threshold slightly now that we've split the chunks
    chunkSizeWarningLimit: 600,
  },
})
