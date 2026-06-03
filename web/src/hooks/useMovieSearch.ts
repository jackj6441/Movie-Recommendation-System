import { useEffect, useState } from "react"
import { apiBase } from "../config"
import type { MovieSuggestion } from "../types"

export function useMovieSearch(searchQuery: string, seeds: MovieSuggestion[]) {
  const [suggestions, setSuggestions] = useState<MovieSuggestion[]>([])
  const [noSearchResults, setNoSearchResults] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const [retryNonce, setRetryNonce] = useState(0)

  useEffect(() => {
    setNoSearchResults(false)
    setSearchError(null)
    if (!searchQuery.trim()) {
      setSuggestions([])
      setSearchLoading(false)
      return
    }

    const controller = new AbortController()
    let cancelled = false
    const run = async () => {
      setSearchLoading(true)
      try {
        const res = await fetch(`${apiBase}/movies/search?q=${encodeURIComponent(searchQuery)}`, {
          signal: controller.signal,
        })
        if (!res.ok) {
          throw new Error("Search failed")
        }
        const json = (await res.json()) as MovieSuggestion[]
        const existing = new Set(seeds.map((seed) => seed.movie_id))
        const filtered = json.filter((item) => !existing.has(item.movie_id))
        if (cancelled) return
        setSuggestions(filtered)
        if (filtered.length === 0) setNoSearchResults(true)
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return
        if (cancelled) return
        setSuggestions([])
        setNoSearchResults(false)
        setSearchError("Movie search is unavailable. Check the API and try again.")
      } finally {
        if (!cancelled) setSearchLoading(false)
      }
    }

    const timer = setTimeout(run, 200)
    return () => {
      cancelled = true
      controller.abort()
      clearTimeout(timer)
    }
  }, [searchQuery, seeds, retryNonce])

  return {
    suggestions,
    noSearchResults,
    searchLoading,
    searchError,
    retrySearch: () => setRetryNonce((value) => value + 1),
    setSuggestions,
  }
}
