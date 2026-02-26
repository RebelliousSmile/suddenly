import { defineConfig } from 'vite'
import UnoCSS from 'unocss/vite'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    UnoCSS(),
  ],
  
  // Build vers le dossier static de Django
  build: {
    outDir: resolve(__dirname, '../static/dist'),
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'src/main.js'),
      },
      output: {
        // Noms de fichiers prévisibles pour Django
        entryFileNames: 'js/[name].js',
        chunkFileNames: 'js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name?.endsWith('.css')) {
            return 'css/[name][extname]'
          }
          return 'assets/[name]-[hash][extname]'
        },
      },
    },
  },
  
  // Serveur de dev avec proxy vers Django
  server: {
    port: 5173,
    proxy: {
      // Proxy tout sauf les assets Vite vers Django
      '^/(?!@|src|node_modules).*': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
