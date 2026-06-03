import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"

const API_TARGET = "http://127.0.0.1:8000"

/** Paths served by reco-api; proxied in dev so any Vite port avoids CORS. */
const API_PROXY_PATHS = [
  "genres",
  "movies",
  "recommendations",
  "explanations",
  "rag",
  "system",
  "healthz",
  "recommend",
  "explain",
  "score",
  "debug",
  "metrics",
  "model",
] as const

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 3000,
    proxy: Object.fromEntries(
      API_PROXY_PATHS.map((segment) => [
        `/${segment}`,
        { target: API_TARGET, changeOrigin: true },
      ])
    ),
  },
})
