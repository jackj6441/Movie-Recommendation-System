import { useCallback, useEffect, useState } from "react"
import { apiBase, PRIORITY_GENRES } from "../config"
import { sortGenres } from "../utils/format"

const MAX_RETRIES = 5

async function fetchGenresOnce(): Promise<string[]> {
  const res = await fetch(`${apiBase}/genres`)
  if (!res.ok) {
    throw new Error("Genres failed")
  }
  const json = (await res.json()) as { name: string }[]
  return sortGenres(
    json.map((item) => item.name),
    PRIORITY_GENRES
  )
}

export function useGenres() {
  const [genres, setGenres] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    for (let attempt = 0; attempt < MAX_RETRIES; attempt += 1) {
      try {
        const names = await fetchGenresOnce()
        setGenres(names)
        setLoading(false)
        return
      } catch {
        if (attempt < MAX_RETRIES - 1) {
          await new Promise((resolve) => setTimeout(resolve, 800 * (attempt + 1)))
        }
      }
    }
    setGenres([])
    setError("Could not load genres. Check that the API is running.")
    setLoading(false)
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return { genres, loading, error, retry: load }
}
