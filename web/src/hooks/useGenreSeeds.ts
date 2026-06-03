import { useEffect, useState } from "react"
import { apiBase } from "../config"
import type { MovieSuggestion } from "../types"

export function useGenreSeeds(selectedGenres: string[]) {
  const [genreSeeds, setGenreSeeds] = useState<MovieSuggestion[]>([])

  useEffect(() => {
    const run = async () => {
      try {
        const targets = selectedGenres.length ? selectedGenres : ["all"]
        const responses = await Promise.all(
          targets.map((genre) =>
            fetch(`${apiBase}/genres/${encodeURIComponent(genre)}/seeds?limit=20`)
          )
        )
        const payloads = await Promise.all(
          responses.map((res) => (res.ok ? res.json() : { seeds: [] }))
        )
        const merged: MovieSuggestion[] = []
        const seen = new Set<number>()
        payloads.forEach((payload: { seeds: MovieSuggestion[] }) => {
          payload.seeds.forEach((seed) => {
            if (!seen.has(seed.movie_id)) {
              seen.add(seed.movie_id)
              merged.push(seed)
            }
          })
        })
        setGenreSeeds(merged.slice(0, 20))
      } catch {
        setGenreSeeds([])
      }
    }
    run()
  }, [selectedGenres])

  return genreSeeds
}
