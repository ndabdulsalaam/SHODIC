import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('/react-icons/')) return 'icons'
          if (
            id.includes('/react-markdown/')
            || id.includes('/remark-gfm/')
            || id.includes('/rehype-raw/')
            || id.includes('/rehype-sanitize/')
          ) {
            return 'markdown'
          }
          if (
            id.includes('/react/')
            || id.includes('/react-dom/')
            || id.includes('/react-router-dom/')
          ) {
            return 'react'
          }
          return undefined
        },
      },
    },
  },
})
