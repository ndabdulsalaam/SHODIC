import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    modulePreload: {
      resolveDependencies(_filename, deps) {
        return deps.filter((dep) => !dep.includes('markdown-'))
      },
    },
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('/react-icons/')) return 'icons'
          if (
            id.includes('/react-markdown/')
            || id.includes('/remark-gfm/')
          ) {
            return 'markdown'
          }
          if (
            id.includes('/react/')
            || id.includes('/react-dom/')
          ) {
            return 'react'
          }
          return undefined
        },
      },
    },
  },
})
