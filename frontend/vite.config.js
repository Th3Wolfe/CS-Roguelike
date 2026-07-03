import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Em dev, o front (5173) encaminha chamadas de API pro Flask (5000).
      // Em produção, o Flask serve o build do Vite diretamente, então esse
      // proxy nunca entra em ação — é só pra conveniência do `npm run dev`.
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      // Escudos, música e outros estáticos que hoje vivem em ui/static
      // continuam servidos pelo Flask até o resto da migração acontecer.
      '/ui': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // Builda pra dentro do projeto Flask, num diretório que app.py vai
    // aprender a servir no lugar do ui/index.html antigo.
    outDir: '../ui_dist',
    emptyOutDir: true,
  },
})
