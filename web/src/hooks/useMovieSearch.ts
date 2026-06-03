import { useEffect, useState } from "react"
import { apiBase } from "../config"
import type { MovieSuggestion } from "../types"

export function useMovieSearch(searchQuery: string, seeds: MovieSuggestion[]) {
  const [suggestions, setSuggestions] = useState<MovieSuggestion[]>([])
  const [noSearchResults, setNoSearchResults] = useState(false)

  useEffect(() => {
    setNoSearchResults(false)
    if (!searchQuery.trim()) {
      setSuggestions([])
      return
    }

    const controller = new AbortController()
    const run = async () => {
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
        setSuggestions(filtered)
        if (filtered.length === 0) setNoSearchResults(true)
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return
        setSuggestions([])
      }
    }

    const timer = setTimeout(run, 200)
    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [searchQuery, seeds])

  return { suggestions, noSearchResults, setSuggestions }
}
