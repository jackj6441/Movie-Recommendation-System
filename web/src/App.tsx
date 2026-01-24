import React, { useEffect, useRef, useState } from "react"
import * as d3 from "d3"

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
  model_version?: string
  explain?: {
    ncf_score: number
    content_score: number
    alpha: number
    similar_movies: RecommendationItem[]
  }
}

type ExplainItem = {
  movie_id: number
  title: string
  ncf: number
  content: number
  final: number
}

type SimilarMovie = {
  movie_id: number
  title: string
  similarity: number
}

type ExplainResponse = {
  user_id: number
  model_version: string
  alpha: number
  anchor_movie: { movie_id: number; title: string } | null
  topk: ExplainItem[]
  similar_movies: SimilarMovie[]
  content_available: boolean
}

const apiBase = import.meta.env.VITE_API_BASE || "http://reco-api:8000"

export default function App() {
  const [userId, setUserId] = useState(1)
  const [k, setK] = useState(10)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<RecommendationResponse | null>(null)
  const [explain, setExplain] = useState<ExplainResponse | null>(null)
  const [explainError, setExplainError] = useState<string | null>(null)
  const chartRef = useRef<SVGSVGElement | null>(null)

  const fetchRecommendations = async () => {
    setLoading(true)
    setError(null)
    setExplainError(null)
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

    try {
      const explainUrl = `${apiBase}/explain?user_id=${userId}&k=${k}`
      const explainRes = await fetch(explainUrl)
      if (!explainRes.ok) {
        throw new Error(`Explain failed: ${explainRes.status}`)
      }
      const explainJson = (await explainRes.json()) as ExplainResponse
      setExplain(explainJson)
    } catch (err) {
      setExplainError(err instanceof Error ? err.message : "Unknown error")
      setExplain(null)
    }
  }

  useEffect(() => {
    if (!explain || !chartRef.current) return
    const items = explain.topk
    if (!items.length) return

    const contentAvailable = explain.content_available
    const stackedItems = items.map((item) => ({
      ...item,
      content: contentAvailable ? item.content : 0,
    }))

    const width = 720
    const rowHeight = 28
    const labelWidth = 240
    const valueWidth = 64
    const barWidth = width - labelWidth - valueWidth - 24
    const height = items.length * rowHeight + 30

    const svg = d3.select(chartRef.current)
    svg.attr("width", width).attr("height", height)
    svg.selectAll("*").remove()

    const maxFinal = d3.max(stackedItems, (d) => d.final) || 1
    const xScale = d3.scaleLinear().domain([0, maxFinal]).range([0, barWidth])

    const group = svg.append("g").attr("transform", "translate(0,10)")

    const row = group
      .selectAll("g")
      .data(stackedItems)
      .enter()
      .append("g")
      .attr("transform", (_, i) => `translate(0, ${i * rowHeight})`)

    row
      .append("text")
      .attr("x", 0)
      .attr("y", rowHeight - 10)
      .attr("font-size", "12px")
      .text((d) => (d.title.length > 34 ? `${d.title.slice(0, 34)}...` : d.title))

    row
      .append("rect")
      .attr("x", labelWidth)
      .attr("y", 6)
      .attr("height", 16)
      .attr("width", (d) => xScale(explain.alpha * d.ncf))
      .attr("fill", "#2f855a")

    row
      .append("rect")
      .attr("x", (d) => labelWidth + xScale(explain.alpha * d.ncf))
      .attr("y", 6)
      .attr("height", 16)
      .attr("width", (d) => xScale((1 - explain.alpha) * d.content))
      .attr("fill", "#c05621")

    row
      .append("text")
      .attr("x", labelWidth + barWidth + 10)
      .attr("y", rowHeight - 10)
      .attr("font-size", "12px")
      .text((d) => d.final.toFixed(3))
  }, [explain])

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
          {data.explain && (
            <div style={{ marginTop: "1.5rem" }}>
              <h2>Explanation</h2>
              <p>model_version: {data.model_version ?? "unknown"}</p>
              <p>
                alpha: {data.explain.alpha} | ncf_score: {data.explain.ncf_score} | content_score: {data.explain.content_score}
              </p>
              <ul>
                {data.explain.similar_movies.map((movie) => (
                  <li key={movie.movie_id}>
                    {movie.title} — {movie.score}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {explain && (
        <section style={{ marginTop: "2rem" }}>
          <h2>Explain</h2>
          <p>
            anchor_movie: {explain.anchor_movie?.title ?? "n/a"} | alpha: {explain.alpha}
          </p>
          {!explain.content_available && (
            <p style={{ color: "#c05621" }}>
              Content unavailable: falling back to NCF-only scores.
            </p>
          )}
          <svg ref={chartRef} />
          <div style={{ marginTop: "1rem" }}>
            <h3>Similar Movies</h3>
            <ul>
              {explain.similar_movies.map((movie) => (
                <li key={movie.movie_id}>
                  {movie.title} — {movie.similarity.toFixed(3)}
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {explainError && <p style={{ color: "crimson" }}>Explain error: {explainError}</p>}
    </main>
  )
}
