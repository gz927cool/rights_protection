import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/chat/stream": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path,
      },
      "/sessions": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/steps": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/upload": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
})
