/** Browser-reachable API base for local dev and Docker. */
export function resolveApiBase(): string {
  const fromEnv = import.meta.env.VITE_API_BASE?.trim()
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
export const MAX_SEEDS = 5

export type TimeRangeKey = "all" | "2020s" | "2010s" | "2000s" | "1990s" | "classics"

export type TimeRange = {
  key: TimeRangeKey
  label: string
  yearMin?: number
  yearMax?: number
}

/** Single-select decade buckets for the results-page time filter. */
export const TIME_RANGES: TimeRange[] = [
  { key: "all", label: "All years" },
  { key: "2020s", label: "2020s", yearMin: 2020, yearMax: 2029 },
  { key: "2010s", label: "2010s", yearMin: 2010, yearMax: 2019 },
  { key: "2000s", label: "2000s", yearMin: 2000, yearMax: 2009 },
  { key: "1990s", label: "1990s", yearMin: 1990, yearMax: 1999 },
  { key: "classics", label: "Classics (pre-1990)", yearMax: 1989 },
]

export function timeRangeBounds(key: TimeRangeKey): { yearMin: number | null; yearMax: number | null } {
  const match = TIME_RANGES.find((range) => range.key === key)
  return { yearMin: match?.yearMin ?? null, yearMax: match?.yearMax ?? null }
}
