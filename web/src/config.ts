/** Browser-reachable API base for local dev and Docker. */
export function resolveApiBase(): string {
  const fromEnv = import.meta.env.VITE_API_BASE?.trim()
  // Vite dev proxies reco-api routes on the same origin (any fallback port).
  if (import.meta.env.DEV && typeof window !== "undefined" && !fromEnv) {
    return ""
  }
  if (typeof window !== "undefined") {
    const pageHost = window.location.hostname
    if (fromEnv) {
      try {
        const url = new URL(fromEnv)
        // Docker sets localhost:8000 but the page may be opened via 127.0.0.1 or a public IP.
        if (url.hostname === "localhost" && pageHost !== "localhost") {
          url.hostname = pageHost
        }
        return url.toString().replace(/\/$/, "")
      } catch {
        return fromEnv.replace(/\/$/, "")
      }
    }
    return `${window.location.protocol}//${pageHost}:8000`
  }
  return fromEnv?.replace(/\/$/, "") || "http://localhost:8000"
}

export const apiBase = resolveApiBase()

export const PRIORITY_GENRES = ["Comedy", "Drama", "Action"] as const

export const MAX_GENRES = 3
