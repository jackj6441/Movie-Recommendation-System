import React, { useState } from "react"

type RecommendationItem = {
  movie_id: number
  title: string
  score: number
}

type RecommendationResponse = {
  user_id: number
  k: number
  cache_hit: boolean
  items: RecommendationItem[]
}

const apiBase = import.meta.env.VITE_API_BASE || "http://reco-api:8000"

export default function App() {
  const [userId, setUserId] = useState(1)
  const [k, setK] = useState(10)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<RecommendationResponse | null>(null)

  const fetchRecommendations = async () => {
    setLoading(true)
    setError(null)
    try {
      const url = `${apiBase}/recommend?user_id=${userId}&k=${k}`
      const res = await fetch(url)
      if (!res.ok) {
        throw new Error(`Request failed: ${res.status}`)
      }
      const json = (await res.json()) as RecommendationResponse
      setData(json)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error")
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>Movie Recommender UI</h1>

      <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
        <label>
          user_id
          <input
            type="number"
            value={userId}
            onChange={(event) => setUserId(Number(event.target.value))}
            style={{ marginLeft: "0.5rem", width: "6rem" }}
          />
        </label>
        <label>
          k
          <input
            type="number"
            value={k}
            onChange={(event) => setK(Number(event.target.value))}
            style={{ marginLeft: "0.5rem", width: "6rem" }}
          />
        </label>
        <button onClick={fetchRecommendations} disabled={loading}>
          {loading ? "Loading..." : "Get Recommendations"}
        </button>
      </div>

      <p style={{ marginTop: "0.5rem", color: "#666", fontSize: "0.9rem" }}>
        apiBase: {apiBase}
      </p>

      {error && <p style={{ color: "crimson" }}>Error: {error}</p>}

      {data && (
        <section style={{ marginTop: "1.5rem" }}>
          <p>
            cache_hit: <strong>{String(data.cache_hit)}</strong>
          </p>
          <ul>
            {data.items.map((item) => (
              <li key={item.movie_id}>
                {item.title} — {item.score}
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  )
}
