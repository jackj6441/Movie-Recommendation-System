import React, { useEffect, useRef, useState } from "react"
import * as d3 from "d3"

type RecommendationItem = {
  movie_id: number
  title: string
  score: number
}

type RecommendationResponse = {
  items: RecommendationItem[]
  seed_movies: { movie_id: number; title: string }[]
  anchor_source: string
  model_version: string
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
  user_id: number | null
  model_version: string
  alpha: number
  anchor_movie: { movie_id: number; title: string } | null
  topk: ExplainItem[]
  similar_movies: SimilarMovie[]
  content_available: boolean
  seed_movies?: { movie_id: number; title: string }[]
  anchor_source?: string
}

type RagExplanationItem = {
  movie_id: number
  reason: string
  evidence: string[]
}

type RagExplanationResponse = {
  summary: string
  items: RagExplanationItem[]
  explanation_source: "rag" | "rag_cache" | "deterministic_fallback"
  fallback_reason?: string | null
}

type MovieSuggestion = {
  movie_id: number
  title: string
}

const apiBase = import.meta.env.VITE_API_BASE || "http://reco-api:8000"

export default function App() {
  const [step, setStep] = useState(1)
  const [genres, setGenres] = useState<string[]>([])
  const [selectedGenres, setSelectedGenres] = useState<string[]>([])
  const [genreSeeds, setGenreSeeds] = useState<MovieSuggestion[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [suggestions, setSuggestions] = useState<MovieSuggestion[]>([])
  const [seeds, setSeeds] = useState<MovieSuggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<RecommendationResponse | null>(null)
  const [explain, setExplain] = useState<ExplainResponse | null>(null)
  const [explainError, setExplainError] = useState<string | null>(null)
  const [ragExplain, setRagExplain] = useState<RagExplanationResponse | null>(null)
  const [ragExplainError, setRagExplainError] = useState<string | null>(null)
  const chartRef = useRef<SVGSVGElement | null>(null)

  const fetchRecommendations = async (shuffle = false) => {
    setLoading(true)
    setError(null)
    setExplainError(null)
    setRagExplainError(null)
    setRagExplain(null)
    try {
      const res = await fetch(`${apiBase}/recommendations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seeds: seeds.map((seed) => seed.movie_id), shuffle }),
      })
      if (!res.ok) {
        throw new Error(`Request failed: ${res.status}`)
      }
      const json = (await res.json()) as RecommendationResponse
      setData(json)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error")
      setData(null)
      return
    } finally {
      setLoading(false)
    }

    try {
      const explainRes = await fetch(`${apiBase}/explanations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seeds: seeds.map((seed) => seed.movie_id), shuffle }),
      })
      if (!explainRes.ok) {
        throw new Error(`Explain failed: ${explainRes.status}`)
      }
      const explainJson = (await explainRes.json()) as ExplainResponse
      setExplain(explainJson)
    } catch (err) {
      setExplainError(err instanceof Error ? err.message : "Unknown error")
      setExplain(null)
    }

    try {
      const ragExplainRes = await fetch(`${apiBase}/rag/explanations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seeds: seeds.map((seed) => seed.movie_id), shuffle }),
      })
      if (!ragExplainRes.ok) {
        throw new Error(`RAG explain failed: ${ragExplainRes.status}`)
      }
      const ragExplainJson = (await ragExplainRes.json()) as RagExplanationResponse
      setRagExplain(ragExplainJson)
    } catch (err) {
      setRagExplainError(err instanceof Error ? err.message : "Unknown error")
      setRagExplain(null)
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

  useEffect(() => {
    const run = async () => {
      try {
        const res = await fetch(`${apiBase}/genres`)
        if (!res.ok) {
          throw new Error("Genres failed")
        }
        const json = (await res.json()) as { name: string }[]
        setGenres(json.map((item) => item.name))
      } catch {
        setGenres([])
      }
    }
    run()
  }, [apiBase])

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
  }, [selectedGenres, apiBase])

  useEffect(() => {
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
        setSuggestions(json.filter((item) => !existing.has(item.movie_id)))
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
  }, [searchQuery, apiBase, seeds])

  return (
    <main className="page">
      <style>{`
        .page {
          font-family: "Cormorant Garamond", "Georgia", serif;
          background:
            radial-gradient(circle at 20% 10%, rgba(255, 240, 214, 0.6), transparent 55%),
            radial-gradient(circle at 85% 0%, rgba(214, 236, 255, 0.5), transparent 45%),
            #fbfaf7;
          min-height: 100vh;
          padding: 2.75rem 1.5rem 3.5rem;
          color: #2b2a28;
        }
        .header {
          max-width: 1120px;
          margin: 0 auto 2rem;
        }
        .title {
          font-size: clamp(2.2rem, 2vw + 1.6rem, 3rem);
          letter-spacing: -0.02em;
          margin: 0 0 0.45rem;
        }
        .subtle {
          color: #6a655f;
          font-size: 0.95rem;
        }
        .progress {
          font-size: 0.95rem;
          color: #7b746d;
          margin-top: 0.35rem;
        }
        .controls {
          display: flex;
          flex-wrap: wrap;
          gap: 0.75rem 1.25rem;
          align-items: center;
          margin-top: 1.1rem;
        }
        .wizard-nav {
          display: flex;
          gap: 0.75rem;
          margin-top: 1.2rem;
          flex-wrap: wrap;
        }
        .search {
          position: relative;
          min-width: 240px;
          flex: 1 1 320px;
        }
        .search input {
          width: 100%;
          padding: 0.55rem 0.75rem;
          border-radius: 10px;
          border: 1px solid #d7cfc4;
          background: #fffdf9;
          font-size: 0.95rem;
        }
        .chips {
          display: flex;
          flex-wrap: wrap;
          gap: 0.55rem;
          margin-top: 1rem;
        }
        .chip {
          border: 1px solid #d7cfc4;
          border-radius: 999px;
          padding: 0.35rem 0.85rem;
          font-size: 0.85rem;
          cursor: pointer;
          background: #fffdf9;
          transition: all 120ms ease;
        }
        .chip:hover {
          border-color: #8aa6c2;
        }
        .chip.active {
          background: #2f855a;
          color: #fff;
          border-color: #2f855a;
        }
        .suggestions {
          position: absolute;
          top: 2.7rem;
          left: 0;
          right: 0;
          background: #fff;
          border: 1px solid #e7e0d7;
          border-radius: 12px;
          box-shadow: 0 16px 36px rgba(30, 24, 12, 0.12);
          max-height: 240px;
          overflow: auto;
          z-index: 5;
        }
        .suggestions button {
          display: block;
          width: 100%;
          text-align: left;
          padding: 0.6rem 0.85rem;
          border: none;
          background: none;
          cursor: pointer;
        }
        .suggestions button:hover {
          background: #f4efe7;
        }
        .controls button {
          padding: 0.5rem 1rem;
          border-radius: 8px;
          border: 1px solid #2f855a;
          background: linear-gradient(135deg, #2f855a, #3a9b6c);
          color: #fff;
          font-weight: 600;
          cursor: pointer;
          box-shadow: 0 6px 16px rgba(47, 133, 90, 0.25);
        }
        .ghost {
          background: transparent;
          color: #2f855a;
          border: 1px solid #2f855a;
          box-shadow: none;
        }
        .controls button:disabled {
          background: #b5c9bd;
          border-color: #b5c9bd;
          cursor: not-allowed;
          box-shadow: none;
        }
        .layout {
          max-width: 1120px;
          margin: 0 auto;
          display: grid;
          grid-template-columns: 1fr;
          gap: 1.75rem;
        }
        @media (min-width: 900px) {
          .layout {
            grid-template-columns: 1fr 1fr;
          }
        }
        .card {
          background: #ffffff;
          border-radius: 18px;
          border: 1px solid #efe7db;
          box-shadow: 0 20px 36px rgba(39, 30, 14, 0.08);
          padding: 1.75rem;
        }
        .card h2 {
          margin: 0 0 0.3rem;
          font-size: 1.45rem;
        }
        .card .subtitle {
          color: #6d6963;
          font-size: 0.92rem;
          margin-bottom: 1.15rem;
        }
        .list {
          display: flex;
          flex-direction: column;
          gap: 0.7rem;
        }
        .row {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          gap: 1rem;
          border-bottom: 1px solid #f1ece4;
          padding-bottom: 0.45rem;
        }
        .row:last-child {
          border-bottom: none;
        }
        .score {
          font-family: "IBM Plex Mono", "Courier New", monospace;
          font-size: 0.95rem;
          color: #2d2a26;
        }
        .featured-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
          gap: 1rem;
          margin-top: 1rem;
        }
        .movie-card {
          min-height: 280px;
          border-radius: 18px;
          padding: 1rem;
          display: flex;
          flex-direction: column;
          justify-content: flex-end;
          overflow: hidden;
          position: relative;
          color: #fffaf2;
          background:
            linear-gradient(180deg, rgba(20, 18, 16, 0.08), rgba(20, 18, 16, 0.88)),
            radial-gradient(circle at 25% 15%, rgba(255, 198, 109, 0.78), transparent 32%),
            radial-gradient(circle at 86% 4%, rgba(111, 155, 202, 0.72), transparent 34%),
            linear-gradient(135deg, #34291f, #111827);
          box-shadow: 0 18px 32px rgba(24, 20, 16, 0.24);
        }
        .movie-card:nth-child(2) {
          background:
            linear-gradient(180deg, rgba(20, 18, 16, 0.08), rgba(20, 18, 16, 0.88)),
            radial-gradient(circle at 20% 10%, rgba(164, 214, 193, 0.78), transparent 32%),
            radial-gradient(circle at 88% 0%, rgba(229, 142, 121, 0.68), transparent 34%),
            linear-gradient(135deg, #24352f, #171b2a);
        }
        .movie-card:nth-child(3) {
          background:
            linear-gradient(180deg, rgba(20, 18, 16, 0.08), rgba(20, 18, 16, 0.88)),
            radial-gradient(circle at 24% 12%, rgba(224, 181, 255, 0.62), transparent 34%),
            radial-gradient(circle at 88% 0%, rgba(250, 214, 122, 0.68), transparent 34%),
            linear-gradient(135deg, #33243d, #14151d);
        }
        .movie-card::before {
          content: "";
          position: absolute;
          inset: 0;
          background-image:
            linear-gradient(rgba(255,255,255,0.06) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px);
          background-size: 18px 18px;
          opacity: 0.35;
        }
        .movie-card > * {
          position: relative;
          z-index: 1;
        }
        .movie-rank {
          position: absolute;
          top: 0.85rem;
          left: 0.85rem;
          font-family: "IBM Plex Mono", "Courier New", monospace;
          font-size: 0.8rem;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: rgba(255, 250, 242, 0.76);
        }
        .movie-card h3 {
          margin: 0 0 0.45rem;
          font-size: 1.25rem;
          line-height: 1.1;
        }
        .movie-reason {
          margin: 0.35rem 0 0;
          color: rgba(255, 250, 242, 0.84);
          font-size: 0.92rem;
        }
        .signal-row {
          display: flex;
          flex-wrap: wrap;
          gap: 0.4rem;
          margin-top: 0.75rem;
        }
        .signal-chip {
          border: 1px solid rgba(255, 250, 242, 0.35);
          border-radius: 999px;
          padding: 0.2rem 0.5rem;
          font-size: 0.72rem;
          color: rgba(255, 250, 242, 0.82);
          background: rgba(255, 255, 255, 0.08);
        }
        .warning {
          color: #c05621;
          margin-bottom: 0.75rem;
        }
        .seeds {
          display: flex;
          flex-wrap: wrap;
          gap: 0.55rem;
          margin-top: 0.85rem;
        }
        .seed {
          background: #f3f5f7;
          border-radius: 999px;
          padding: 0.35rem 0.75rem;
          font-size: 0.85rem;
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
        }
        .seed button {
          border: none;
          background: none;
          cursor: pointer;
          font-weight: 700;
        }
      `}</style>

      <section className="header">
        <h1 className="title">Movie Recommender UI</h1>
        <div className="progress">{step}/3 选择类型 → 选择电影 → 推荐结果</div>
        <p className="subtle">apiBase: {apiBase}</p>
        {error && <p style={{ color: "crimson" }}>Error: {error}</p>}
        {explainError && <p style={{ color: "crimson" }}>Explain error: {explainError}</p>}
        {ragExplainError && <p className="warning">AI explanation unavailable. Showing recommendations normally.</p>}
      </section>

      <section className="layout">
        {step === 1 && (
          <div className="card">
            <h2>选择类型</h2>
            <div className="subtitle">建议先选 1–3 个类型</div>
            <div className="chips">
              {["Comedy", "Drama", "Action"].map((genre) => (
                <button
                  key={genre}
                  className={`chip ${selectedGenres.includes(genre) ? "active" : ""}`}
                  onClick={() =>
                    setSelectedGenres((prev) =>
                      prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre]
                    )
                  }
                >
                  {genre}
                </button>
              ))}
            </div>
            <div className="chips">
              {genres
                .filter((genre) => !["Comedy", "Drama", "Action"].includes(genre))
                .map((genre) => (
                <button
                  key={genre}
                  className={`chip ${selectedGenres.includes(genre) ? "active" : ""}`}
                  onClick={() =>
                    setSelectedGenres((prev) =>
                      prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre]
                    )
                  }
                >
                  {genre}
                </button>
                ))}
            </div>
            <div className="wizard-nav">
              <button
                className="ghost"
                onClick={() => {
                  setSelectedGenres([])
                  setStep(2)
                }}
              >
                跳过
              </button>
              <button onClick={() => setStep(2)}>下一步</button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="card">
            <h2>选择电影</h2>
            <div className="subtitle">选择 1–5 部电影作为种子</div>
            <div className="controls">
              <div className="search">
                <input
                  type="text"
                  placeholder="搜索电影..."
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                />
                {suggestions.length > 0 && (
                  <div className="suggestions">
                    {suggestions.map((movie) => (
                      <button
                        key={movie.movie_id}
                        onClick={() => {
                          if (seeds.length >= 5) return
                          setSeeds((prev) => [...prev, movie])
                          setSearchQuery("")
                          setSuggestions([])
                        }}
                      >
                        {movie.title}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <button
                onClick={async () => {
                  await fetchRecommendations(false)
                  setStep(3)
                }}
                disabled={loading || seeds.length === 0 || seeds.length > 5}
              >
                {loading ? "Loading..." : "Recommend"}
              </button>
            </div>
            <div className="seeds">
              <span className="subtle">Selected ({seeds.length}/5):</span>
              {seeds.map((seed) => (
                <span className="seed" key={seed.movie_id}>
                  {seed.title}
                  <button
                    onClick={() =>
                      setSeeds((prev) => prev.filter((item) => item.movie_id !== seed.movie_id))
                    }
                    aria-label={`Remove ${seed.title}`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
            <div style={{ marginTop: "1rem" }}>
              <h3>Recommended Seeds</h3>
              <div className="list">
                {genreSeeds.map((movie) => (
                  <div className="row" key={movie.movie_id}>
                    <span>{movie.title}</span>
                    <button
                      className="ghost"
                      onClick={() => {
                        if (seeds.length >= 5) return
                        if (seeds.find((seed) => seed.movie_id === movie.movie_id)) return
                        setSeeds((prev) => [...prev, movie])
                      }}
                    >
                      选择
                    </button>
                  </div>
                ))}
              </div>
            </div>
            <div className="wizard-nav">
              <button className="ghost" onClick={() => setStep(1)}>
                返回
              </button>
              <button
                className="ghost"
                onClick={() => {
                  setSeeds([])
                  setSearchQuery("")
                  setSuggestions([])
                }}
              >
                重新选择
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <>
            <div className="card">
              <h2>Featured for you</h2>
              <div className="subtitle">
                anchor_source: {data?.anchor_source ?? "-"} · model_version: {data?.model_version ?? "-"}
              </div>
              <p className="subtle">
                根据你选择的【{selectedGenres.join(", ") || "未选择类型"}】和 {seeds.length} 部种子电影，为你找到了最相似的 10 部。
              </p>
              <div className="featured-grid">
                {data?.items.slice(0, 3).map((recommendation, index) => {
                  const ragItem = ragExplain?.items.find((item) => item.movie_id === recommendation.movie_id)

                  return (
                    <article className="movie-card" key={recommendation.movie_id}>
                      <span className="movie-rank">Top {index + 1}</span>
                      <h3>{recommendation.title}</h3>
                      <span className="score">{recommendation.score.toFixed(3)}</span>
                      {ragItem && <p className="movie-reason">{ragItem.reason}</p>}
                      <div className="signal-row">
                        <span className="signal-chip">Seed match</span>
                        <span className="signal-chip">Content signal</span>
                        <span className="signal-chip">Hybrid score</span>
                      </div>
                    </article>
                  )
                })}
              </div>
              <div className="wizard-nav">
                <button onClick={() => fetchRecommendations(true)} disabled={loading}>
                  {loading ? "Loading..." : "换一批"}
                </button>
                <button
                  className="ghost"
                  onClick={() => {
                    setStep(1)
                    setSeeds([])
                    setSearchQuery("")
                    setSuggestions([])
                  }}
                >
                  重新开始
                </button>
                <button className="ghost" onClick={() => setStep(2)}>
                  返回
                </button>
              </div>
            </div>

            <div className="card">
              <h2>More recommendations</h2>
              <div className="subtitle">Additional matches keep score context only.</div>
              <div className="list">
                {data?.items.slice(3).map((item) => (
                  <div className="row" key={item.movie_id}>
                    <span>{item.title}</span>
                    <span className="score">{item.score.toFixed(3)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <h2>AI Explanation</h2>
              <div className="subtitle">Grounded summary for the top recommendations.</div>
              {ragExplain?.explanation_source === "deterministic_fallback" && (
                <p className="warning">Generated explanation unavailable; showing a safe fallback.</p>
              )}
              {ragExplain ? (
                <>
                  <p>{ragExplain.summary}</p>
                  <div className="list">
                    {data?.items.slice(0, 3).map((recommendation) => {
                      const item = ragExplain.items.find(
                        (ragItem) => ragItem.movie_id === recommendation.movie_id
                      )

                      if (!item) return null

                      return (
                        <div className="row" key={item.movie_id}>
                          <span>{recommendation.title}</span>
                          <span>{item.reason}</span>
                        </div>
                      )
                    })}
                  </div>
                </>
              ) : (
                <p className="subtle">AI explanation will appear here when available.</p>
              )}
            </div>

            <div className="card">
              <h2>Explain</h2>
              <div className="subtitle">
                model_version: {explain?.model_version ?? "-"} · alpha: {explain?.alpha ?? "-"}
              </div>
              <p>
                anchor_movie: {explain?.anchor_movie?.title ?? "n/a"}
              </p>
              {!explain?.content_available && (
                <p className="warning">Content unavailable: falling back to NCF-only scores.</p>
              )}
              <svg ref={chartRef} />
              <div style={{ marginTop: "1rem" }}>
                <h3>Similar Movies</h3>
                <div className="list">
                  {explain?.similar_movies.map((movie) => (
                    <div className="row" key={movie.movie_id}>
                      <span>{movie.title}</span>
                      <span className="score">{movie.similarity.toFixed(3)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}
      </section>
    </main>
  )
}
