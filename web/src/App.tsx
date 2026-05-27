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

function formatTitle(raw: string): string {
  return raw.replace(/^(.*),\s+(The|A|An)\s+(\(\d{4}\))$/, "$2 $1 $3")
}

export default function App() {
  const [step, setStep] = useState(1)
  const [genres, setGenres] = useState<string[]>([])
  const [selectedGenres, setSelectedGenres] = useState<string[]>([])
  const [genreSeeds, setGenreSeeds] = useState<MovieSuggestion[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [suggestions, setSuggestions] = useState<MovieSuggestion[]>([])
  const [seeds, setSeeds] = useState<MovieSuggestion[]>([])
  const [suggestionIndex, setSuggestionIndex] = useState(-1)
  const [noSearchResults, setNoSearchResults] = useState(false)
  const [resultsJustArrived, setResultsJustArrived] = useState(false)
  const [loading, setLoading] = useState(false)
  const [ragLoading, setRagLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<RecommendationResponse | null>(null)
  const [explain, setExplain] = useState<ExplainResponse | null>(null)
  const [explainError, setExplainError] = useState<string | null>(null)
  const [ragExplain, setRagExplain] = useState<RagExplanationResponse | null>(null)
  const [ragExplainError, setRagExplainError] = useState<string | null>(null)
  const chartRef = useRef<SVGSVGElement | null>(null)

  const fetchRecommendations = async (shuffle = false) => {
    setLoading(true)
    setRagLoading(true)
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
      setResultsJustArrived(true)
      setTimeout(() => setResultsJustArrived(false), 1200)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error")
      setData(null)
      setRagLoading(false)
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
    } finally {
      setRagLoading(false)
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
    svg.append("title").text("Hybrid score breakdown — green: collaborative filtering, orange: content signal")

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
      .text((d) => { const t = formatTitle(d.title); return t.length > 34 ? `${t.slice(0, 34)}...` : t })

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
  }, [searchQuery, apiBase, seeds])

  useEffect(() => { setSuggestionIndex(-1) }, [suggestions])

  const handleSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!suggestions.length) return
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setSuggestionIndex(prev => (prev + 1) % suggestions.length)
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setSuggestionIndex(prev => (prev <= 0 ? suggestions.length - 1 : prev - 1))
    } else if (e.key === "Enter" && suggestionIndex >= 0) {
      e.preventDefault()
      const movie = suggestions[suggestionIndex]
      if (seeds.length >= 5) return
      setSeeds(prev => [...prev, movie])
      setSearchQuery("")
      setSuggestions([])
    } else if (e.key === "Escape") {
      setSuggestions([])
    }
  }

  return (
    <main className="page">
      <style>{`
        .page {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
          background:
            radial-gradient(circle at 20% 10%, rgba(255, 240, 214, 0.6), transparent 55%),
            radial-gradient(circle at 85% 0%, rgba(214, 236, 255, 0.5), transparent 45%),
            #fbfaf7;
          min-height: 100vh;
          padding: 2.75rem 1.5rem 3.5rem;
          color: #2b2a28;
          font-size: 1rem;
          line-height: 1.5;
        }
        *:focus-visible {
          outline: 2px solid #2f855a;
          outline-offset: 2px;
          border-radius: 4px;
        }
        .header {
          max-width: 1120px;
          margin: 0 auto 2rem;
        }
        .title {
          font-family: "Cormorant Garamond", "Georgia", serif;
          font-size: clamp(2.2rem, 2vw + 1.6rem, 3rem);
          letter-spacing: -0.02em;
          line-height: 1.1;
          margin: 0 0 0.45rem;
        }
        .subtle {
          color: #6a655f;
          font-size: 0.875rem;
        }
        .progress {
          font-size: 0.875rem;
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
          font-size: 1rem;
          font-family: inherit;
          transition: border-color 150ms ease, box-shadow 150ms ease;
        }
        .search input:focus {
          outline: none;
          border-color: #2f855a;
          box-shadow: 0 0 0 3px rgba(47, 133, 90, 0.12);
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
          font-size: 0.875rem;
          cursor: pointer;
          background: #fffdf9;
          transition: background 140ms cubic-bezier(0.25, 1, 0.5, 1),
                      border-color 140ms cubic-bezier(0.25, 1, 0.5, 1),
                      color 140ms cubic-bezier(0.25, 1, 0.5, 1),
                      transform 100ms cubic-bezier(0.25, 1, 0.5, 1);
        }
        .chip:hover {
          border-color: #8aa6c2;
        }
        .chip:active {
          transform: scale(0.94);
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
          animation: fade-in-up 150ms cubic-bezier(0.25, 1, 0.5, 1) both;
        }
        .suggestions button {
          display: block;
          width: 100%;
          text-align: left;
          padding: 0.6rem 0.85rem;
          border: none;
          background: none;
          cursor: pointer;
          font-family: inherit;
          font-size: 0.9375rem;
        }
        .suggestions button:hover,
        .suggestions button.focused {
          background: #f4efe7;
        }
        .suggestions button.focused {
          outline: 2px solid #2f855a;
          outline-offset: -2px;
        }
        .controls button:not(.ghost),
        .wizard-nav button:not(.ghost) {
          padding: 0.5rem 1rem;
          border-radius: 8px;
          border: 1px solid #2f855a;
          background: linear-gradient(135deg, #2f855a, #3a9b6c);
          color: #fff;
          font-weight: 600;
          font-family: inherit;
          font-size: 0.9375rem;
          cursor: pointer;
          box-shadow: 0 6px 16px rgba(47, 133, 90, 0.25);
          transition: transform 150ms cubic-bezier(0.25, 1, 0.5, 1),
                      box-shadow 150ms cubic-bezier(0.25, 1, 0.5, 1);
        }
        .controls button:not(.ghost):not(:disabled):hover,
        .wizard-nav button:not(.ghost):not(:disabled):hover {
          box-shadow: 0 8px 20px rgba(47, 133, 90, 0.38);
          transform: translateY(-1px);
        }
        .ghost {
          background: transparent;
          color: #2f855a;
          border: 1px solid #2f855a;
          box-shadow: none;
          padding: 0.5rem 1rem;
          border-radius: 8px;
          font-weight: 600;
          font-family: inherit;
          font-size: 0.9375rem;
          cursor: pointer;
          transition: background 150ms cubic-bezier(0.25, 1, 0.5, 1);
        }
        .ghost:not(:disabled):hover {
          background: rgba(47, 133, 90, 0.06);
        }
        .controls button:not(:disabled):active,
        .wizard-nav button:not(:disabled):active {
          transform: scale(0.97);
          transition: transform 80ms cubic-bezier(0.25, 1, 0.5, 1);
        }
        .controls button:not(.ghost):disabled,
        .wizard-nav button:not(.ghost):disabled {
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
          gap: 1.5rem;
        }
        @media (min-width: 900px) {
          .layout {
            grid-template-columns: 1fr 1fr;
          }
        }
        .full-width {
          grid-column: 1 / -1;
        }
        @keyframes fade-in-up {
          from { opacity: 0; transform: translateY(10px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes scale-in {
          from { opacity: 0; transform: scale(0.82); }
          to   { opacity: 1; transform: scale(1); }
        }
        @keyframes card-arrive {
          0%   { box-shadow: 0 20px 36px rgba(39, 30, 14, 0.08); }
          35%  { box-shadow: 0 20px 36px rgba(39, 30, 14, 0.08), 0 0 0 3px rgba(47, 133, 90, 0.28); }
          100% { box-shadow: 0 20px 36px rgba(39, 30, 14, 0.08); }
        }
        .card.arrived {
          animation: card-arrive 1000ms cubic-bezier(0.25, 1, 0.5, 1) both;
        }
        .card {
          background: #ffffff;
          border-radius: 18px;
          border: 1px solid #efe7db;
          box-shadow: 0 20px 36px rgba(39, 30, 14, 0.08);
          padding: 1.75rem;
          animation: fade-in-up 220ms cubic-bezier(0.25, 1, 0.5, 1) both;
        }
        .card h2 {
          font-family: "Cormorant Garamond", "Georgia", serif;
          margin: 0 0 0.3rem;
          font-size: 1.5rem;
          line-height: 1.2;
          letter-spacing: -0.01em;
        }
        .card h3 {
          font-family: "Cormorant Garamond", "Georgia", serif;
          font-size: 1.15rem;
          line-height: 1.2;
          letter-spacing: -0.01em;
        }
        .card .subtitle {
          color: #6d6963;
          font-size: 0.875rem;
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
          font-size: 0.8125rem;
          color: #2d2a26;
          font-variant-numeric: tabular-nums;
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
          animation: fade-in-up 260ms cubic-bezier(0.25, 1, 0.5, 1) both;
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
        .movie-card:nth-child(1) { animation-delay: 0ms; }
        .movie-card:nth-child(2) { animation-delay: 65ms; }
        .movie-card:nth-child(3) { animation-delay: 130ms; }
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
          font-size: 0.75rem;
          letter-spacing: 0.06em;
          color: rgba(255, 250, 242, 0.6);
        }
        .movie-card h3 {
          font-family: "Cormorant Garamond", "Georgia", serif;
          margin: 0 0 0.45rem;
          font-size: 1.3rem;
          line-height: 1.15;
          letter-spacing: -0.01em;
        }
        .movie-reason {
          margin: 0.35rem 0 0;
          color: rgba(255, 250, 242, 0.84);
          font-size: 0.875rem;
          line-height: 1.45;
        }
        .signal-row {
          display: flex;
          flex-wrap: wrap;
          gap: 0.4rem;
          margin-top: 0.75rem;
        }
        .signal-chip {
          border: 1px solid rgba(255, 250, 242, 0.3);
          border-radius: 999px;
          padding: 0.2rem 0.55rem;
          font-size: 0.75rem;
          color: rgba(255, 250, 242, 0.78);
          background: rgba(255, 255, 255, 0.08);
          line-height: 1.4;
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
          font-size: 0.875rem;
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          animation: scale-in 180ms cubic-bezier(0.25, 1, 0.5, 1) both;
        }
        .seed button {
          border: none;
          background: none;
          cursor: pointer;
          font-weight: 700;
          padding: 0.4rem 0.35rem;
          margin: -0.4rem -0.25rem -0.4rem 0;
          min-width: 28px;
          min-height: 28px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 4px;
        }
        .seed button:hover {
          background: rgba(0, 0, 0, 0.07);
        }
        .seed-banner {
          grid-column: 1 / -1;
          animation: fade-in-up 180ms cubic-bezier(0.25, 1, 0.5, 1) both;
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 0.5rem 0.75rem;
          padding: 0.75rem 1rem;
          background: rgba(47, 133, 90, 0.07);
          border: 1px solid rgba(47, 133, 90, 0.15);
          border-radius: 12px;
          font-size: 0.875rem;
          color: #4a5568;
        }
        .seed-banner-label {
          font-weight: 600;
          color: #2f855a;
          white-space: nowrap;
        }
        .disclosure {
          grid-column: 1 / -1;
          border: 1px solid #efe7db;
          border-radius: 18px;
          background: #ffffff;
          box-shadow: 0 2px 8px rgba(39, 30, 14, 0.04);
          overflow: hidden;
        }
        .disclosure summary {
          list-style: none;
          padding: 1.1rem 1.75rem;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 0.6rem;
          font-weight: 600;
          font-size: 0.9375rem;
          color: #4a5568;
          user-select: none;
        }
        .disclosure summary::-webkit-details-marker { display: none; }
        .disclosure summary::before {
          content: "›";
          font-size: 1.1rem;
          line-height: 1;
          transition: transform 150ms ease-out;
          display: inline-block;
          color: #2f855a;
        }
        .disclosure[open] summary::before {
          transform: rotate(90deg);
        }
        .disclosure summary:hover {
          background: #faf7f3;
        }
        .disclosure summary:focus-visible {
          outline: 2px solid #2f855a;
          outline-offset: -2px;
          border-radius: 12px;
        }
        .disclosure-body {
          padding: 0 1.75rem 1.75rem;
          border-top: 1px solid #f1ece4;
        }
        .seed-cap-notice {
          font-size: 0.8125rem;
          color: #c05621;
          margin-top: 0.5rem;
        }
        .seeds-empty {
          color: #9b9590;
          font-size: 0.875rem;
          font-style: italic;
          margin-top: 0.5rem;
        }
        .no-results {
          position: absolute;
          top: 2.7rem;
          left: 0;
          right: 0;
          background: #fff;
          border: 1px solid #e7e0d7;
          border-radius: 12px;
          box-shadow: 0 8px 24px rgba(30, 24, 12, 0.08);
          padding: 0.75rem 0.85rem;
          font-size: 0.875rem;
          color: #9b9590;
          z-index: 5;
        }
        .skeleton {
          background: linear-gradient(90deg, #f0ece6 25%, #e8e2da 50%, #f0ece6 75%);
          background-size: 200% 100%;
          animation: shimmer 1.4s ease-in-out infinite;
          border-radius: 6px;
          height: 1rem;
        }
        .skeleton-text {
          height: 0.875rem;
          margin-bottom: 0.5rem;
          border-radius: 4px;
        }
        .skeleton-text:last-child {
          width: 60%;
          margin-bottom: 0;
        }
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
        @media (prefers-reduced-motion: reduce) {
          .skeleton {
            animation: none;
            background: #f0ece6;
          }
          .card,
          .card.arrived,
          .seed-banner,
          .seed,
          .movie-card,
          .suggestions {
            animation: none;
          }
          .chip,
          .controls button,
          .wizard-nav button {
            transition-duration: 0.01ms !important;
          }
        }
        .retry-btn {
          margin-top: 0.75rem;
          padding: 0.4rem 0.9rem;
          border-radius: 8px;
          border: 1px solid #c05621;
          background: transparent;
          color: #c05621;
          font-size: 0.875rem;
          font-family: inherit;
          cursor: pointer;
          transition: background 150ms ease, transform 100ms ease;
        }
        .retry-btn:hover {
          background: rgba(192, 86, 33, 0.06);
        }
        .retry-btn:active {
          transform: scale(0.97);
        }
        .error-text {
          color: #c53030;
          margin: 0;
        }
      `}</style>

      <section className="header">
        <h1 className="title">Movie Recommender UI</h1>
        <div className="progress">{step}/3 Select Genres → Select Movies → Results</div>
        {error && (
          <div>
            <p className="error-text">Couldn't load recommendations. Check your connection and try again.</p>
            <button className="retry-btn" onClick={() => fetchRecommendations(false)}>Try again</button>
          </div>
        )}
        {explainError && <p className="error-text">Score details couldn't load. Your recommendations are still shown above.</p>}
        {ragExplainError && <p className="warning">AI explanation unavailable. Your recommendations are still accurate.</p>}
      </section>

      <section className="layout">
        {step === 1 && (
          <div className="card">
            <h2>Select Genres</h2>
            <div className="subtitle">Choose 1–3 genres to narrow your seeds</div>
            <div className="chips" role="group" aria-label="Common genres">
              {["Comedy", "Drama", "Action"].map((genre) => (
                <button
                  key={genre}
                  className={`chip ${selectedGenres.includes(genre) ? "active" : ""}`}
                  aria-pressed={selectedGenres.includes(genre)}
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
            <div className="chips" role="group" aria-label="More genres">
              {genres
                .filter((genre) => !["Comedy", "Drama", "Action"].includes(genre))
                .map((genre) => (
                <button
                  key={genre}
                  className={`chip ${selectedGenres.includes(genre) ? "active" : ""}`}
                  aria-pressed={selectedGenres.includes(genre)}
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
                Skip
              </button>
              <button onClick={() => setStep(2)}>Next</button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="card">
            <h2>Select Movies</h2>
            <div className="subtitle">Pick 1–5 seed movies</div>
            <div className="controls">
              <div className="search">
                <input
                  type="text"
                  placeholder="Search movies..."
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  onKeyDown={handleSearchKeyDown}
                  role="combobox"
                  aria-expanded={suggestions.length > 0}
                  aria-autocomplete="list"
                  aria-controls="search-suggestions"
                  aria-activedescendant={suggestionIndex >= 0 ? `suggestion-${suggestions[suggestionIndex]?.movie_id}` : undefined}
                  autoComplete="off"
                />
                {suggestions.length > 0 && (
                  <div className="suggestions" id="search-suggestions" role="listbox">
                    {suggestions.map((movie, idx) => (
                      <button
                        key={movie.movie_id}
                        id={`suggestion-${movie.movie_id}`}
                        role="option"
                        aria-selected={idx === suggestionIndex}
                        className={idx === suggestionIndex ? "focused" : ""}
                        onClick={() => {
                          if (seeds.length >= 5) return
                          setSeeds((prev) => [...prev, movie])
                          setSearchQuery("")
                          setSuggestions([])
                        }}
                      >
                        {formatTitle(movie.title)}
                      </button>
                    ))}
                  </div>
                )}
                {noSearchResults && searchQuery.trim() && (
                  <div className="no-results" role="status" aria-live="polite">
                    No movies found for "{searchQuery.trim()}"
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
                {loading ? "Finding your movies…" : "Recommend"}
              </button>
            </div>
            <div className="seeds">
              <span className="subtle">Selected ({seeds.length}/5):</span>
              {seeds.length === 0 && (
                <span className="seeds-empty">Search for a movie above, or select one from the list below.</span>
              )}
              {seeds.length >= 5 && (
                <span className="seed-cap-notice">Maximum reached — remove a movie to add another.</span>
              )}
              {seeds.map((seed) => (
                <span className="seed" key={seed.movie_id}>
                  {formatTitle(seed.title)}
                  <button
                    onClick={() =>
                      setSeeds((prev) => prev.filter((item) => item.movie_id !== seed.movie_id))
                    }
                    aria-label={`Remove ${formatTitle(seed.title)}`}
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
                    <span>{formatTitle(movie.title)}</span>
                    <button
                      className="ghost"
                      onClick={() => {
                        if (seeds.length >= 5) return
                        if (seeds.find((seed) => seed.movie_id === movie.movie_id)) return
                        setSeeds((prev) => [...prev, movie])
                      }}
                    >
                      Select
                    </button>
                  </div>
                ))}
              </div>
            </div>
            <div className="wizard-nav">
              <button className="ghost" onClick={() => setStep(1)}>
                Back
              </button>
              <button
                className="ghost"
                onClick={() => {
                  setSeeds([])
                  setSearchQuery("")
                  setSuggestions([])
                }}
              >
                Clear selection
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <>
            {/* Seed banner — lightweight, no card chrome */}
            <div className="seed-banner">
              <span className="seed-banner-label">Seeds:</span>
              {seeds.map((seed) => (
                <span className="seed" key={seed.movie_id}>
                  {formatTitle(seed.title)}
                </span>
              ))}
              {selectedGenres.length > 0 && (
                <span style={{ color: "#6a655f", marginLeft: "0.25rem" }}>
                  · {selectedGenres.join(", ")}
                </span>
              )}
            </div>

            {/* Featured — full width, primary content */}
            <div className={`card full-width${resultsJustArrived ? " arrived" : ""}`}>
              <h2>Featured for you</h2>
              <div className="subtitle">
                Your top {Math.min(data?.items.length ?? 0, 3)} picks
              </div>
              <div className="featured-grid">
                {data?.items.slice(0, 3).map((recommendation, index) => {
                  const ragItem = ragExplain?.items.find((item) => item.movie_id === recommendation.movie_id)

                  return (
                    <article className="movie-card" key={recommendation.movie_id}>
                      <span className="movie-rank">#{index + 1}</span>
                      <h3>{formatTitle(recommendation.title)}</h3>
                      {ragItem && <p className="movie-reason">{ragItem.reason}</p>}
                      {ragItem && ragItem.evidence.length > 0 && (
                        <div className="signal-row">
                          {ragItem.evidence.slice(0, 3).map((ev, i) => (
                            <span className="signal-chip" key={i}>{ev}</span>
                          ))}
                        </div>
                      )}
                    </article>
                  )
                })}
              </div>
              <div className="wizard-nav">
                <button onClick={() => fetchRecommendations(true)} disabled={loading || ragLoading}>
                  {loading ? "Shuffling…" : "Shuffle"}
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
                  Start over
                </button>
                <button className="ghost" onClick={() => setStep(2)}>
                  Back
                </button>
              </div>
            </div>

            {/* Secondary row: AI explanation + more movies side by side */}
            <div className="card">
              <h2>Why these movies?</h2>
              <div className="subtitle">An AI explanation of your top picks.</div>
              {ragExplain?.explanation_source === "deterministic_fallback" && (
                <p className="warning">Personalized explanation unavailable — showing a general summary instead.</p>
              )}
              {ragExplain ? (
                <p>{ragExplain.summary}</p>
              ) : ragLoading ? (
                <div aria-live="polite" aria-label="Generating explanation">
                  <div className="skeleton skeleton-text" />
                  <div className="skeleton skeleton-text" />
                  <div className="skeleton skeleton-text" />
                </div>
              ) : (
                <p className="subtle">No explanation available for this set of recommendations.</p>
              )}
            </div>

            {(data?.items.length ?? 0) > 3 && (
              <div className="card">
                <h2>More movies you might like</h2>
                <div className="subtitle">More matches ranked by the same model.</div>
                <div className="list">
                  {data?.items.slice(3).map((item) => (
                    <div className="row" key={item.movie_id}>
                      <span>{formatTitle(item.title)}</span>
                      <span className="score">{item.score.toFixed(3)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Score breakdown — collapsed by default, power-user content */}
            <details className="disclosure">
              <summary>Score breakdown</summary>
              <div className="disclosure-body">
                <p className="subtle" style={{ marginBottom: "1rem" }}>How the hybrid model ranked your recommendations.</p>
                {explain?.anchor_movie && (
                  <p className="subtle" style={{ marginBottom: "0.75rem" }}>
                    Anchored on <strong>{formatTitle(explain.anchor_movie.title)}</strong>
                  </p>
                )}
                {!explain?.content_available && (
                  <p className="warning">Content embeddings unavailable — scores are based on collaborative filtering only.</p>
                )}
                <svg ref={chartRef} role="img" aria-label="Hybrid score breakdown: green bars show collaborative filtering contribution, orange bars show content signal contribution" />
                <div style={{ marginTop: "1.25rem" }}>
                  <h3>Similar movies to your seeds</h3>
                  <div className="list" style={{ marginTop: "0.75rem" }}>
                    {explain?.similar_movies.map((movie) => (
                      <div className="row" key={movie.movie_id}>
                        <span>{formatTitle(movie.title)}</span>
                        <span className="score">{movie.similarity.toFixed(3)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </details>
          </>
        )}
      </section>
    </main>
  )
}
