import { useCallback, useState } from "react"
import { apiBase, MAX_GENRES } from "./config"
import { AppShell } from "./components/layout/AppShell"
import { GenreStep } from "./components/genres/GenreStep"
import { SeedStep } from "./components/seeds/SeedStep"
import { ResultsStep } from "./components/results/ResultsStep"
import { EvidenceDashboard } from "./components/evidence/EvidenceDashboard"
import { useGenres } from "./hooks/useGenres"
import { useGenreSeeds } from "./hooks/useGenreSeeds"
import { useMovieSearch } from "./hooks/useMovieSearch"
import type {
  ExplainResponse,
  MovieSuggestion,
  RagExplanationResponse,
  RecommendationResponse,
  SystemEvidence,
} from "./types"

export default function App() {
  const [view, setView] = useState<"recommender" | "evidence">("recommender")
  const [step, setStep] = useState(1)
  const { genres, loading: genresLoading, error: genresError, retry: retryGenres } = useGenres()
  const [selectedGenres, setSelectedGenres] = useState<string[]>([])
  const genreSeeds = useGenreSeeds(selectedGenres)
  const [searchQuery, setSearchQuery] = useState("")
  const [seeds, setSeeds] = useState<MovieSuggestion[]>([])
  const { suggestions, noSearchResults, setSuggestions } = useMovieSearch(searchQuery, seeds)
  const [resultsJustArrived, setResultsJustArrived] = useState(false)
  const [loading, setLoading] = useState(false)
  const [ragLoading, setRagLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<RecommendationResponse | null>(null)
  const [explain, setExplain] = useState<ExplainResponse | null>(null)
  const [explainError, setExplainError] = useState<string | null>(null)
  const [ragExplain, setRagExplain] = useState<RagExplanationResponse | null>(null)
  const [ragExplainError, setRagExplainError] = useState<string | null>(null)
  const [systemEvidence, setSystemEvidence] = useState<SystemEvidence | null>(null)
  const [systemEvidenceLoading, setSystemEvidenceLoading] = useState(false)
  const [systemEvidenceError, setSystemEvidenceError] = useState<string | null>(null)

  const fetchRecommendations = useCallback(
    async (shuffle = false) => {
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
    },
    [seeds]
  )

  const fetchSystemEvidence = useCallback(async () => {
    setSystemEvidenceLoading(true)
    setSystemEvidenceError(null)
    try {
      const res = await fetch(`${apiBase}/system/evidence`)
      if (!res.ok) {
        throw new Error(`Evidence failed: ${res.status}`)
      }
      const json = (await res.json()) as SystemEvidence
      setSystemEvidence(json)
    } catch (err) {
      setSystemEvidenceError(err instanceof Error ? err.message : "Unknown error")
      setSystemEvidence(null)
    } finally {
      setSystemEvidenceLoading(false)
    }
  }, [])

  const handleViewChange = (next: "recommender" | "evidence") => {
    setView(next)
    if (next === "evidence" && !systemEvidence && !systemEvidenceLoading) {
      fetchSystemEvidence()
    }
  }

  const toggleGenre = (genre: string) => {
    setSelectedGenres((prev) => {
      if (prev.includes(genre)) {
        return prev.filter((g) => g !== genre)
      }
      if (prev.length >= MAX_GENRES) return prev
      return [...prev, genre]
    })
  }

  const addSeed = (movie: MovieSuggestion) => {
    setSeeds((prev) => [...prev, movie])
    setSearchQuery("")
    setSuggestions([])
  }

  const resetWizard = () => {
    setStep(1)
    setSeeds([])
    setSearchQuery("")
    setSuggestions([])
    setSelectedGenres([])
    setData(null)
    setExplain(null)
    setRagExplain(null)
    setError(null)
    setExplainError(null)
    setRagExplainError(null)
  }

  const headerAlerts = (
    <>
      {error && (
        <div>
          <p className="error-text">Couldn&apos;t load recommendations. Check your connection and try again.</p>
          <button type="button" className="retry-btn" onClick={() => fetchRecommendations(false)}>
            Try again
          </button>
        </div>
      )}
      {explainError && (
        <p className="error-text">Score details couldn&apos;t load. Your recommendations are still shown above.</p>
      )}
      {ragExplainError && (
        <p className="warning">AI explanation unavailable. Your recommendations are still accurate.</p>
      )}
    </>
  )

  return (
    <AppShell view={view} step={step} onViewChange={handleViewChange} headerAlerts={headerAlerts}>
      {view === "evidence" ? (
        <EvidenceDashboard
          evidence={systemEvidence}
          loading={systemEvidenceLoading}
          error={systemEvidenceError}
          onRetry={fetchSystemEvidence}
        />
      ) : (
        <section className="layout">
          {step === 1 && (
            <GenreStep
              genres={genres}
              loading={genresLoading}
              error={genresError}
              selectedGenres={selectedGenres}
              onToggleGenre={toggleGenre}
              onRetry={retryGenres}
              onSkip={() => {
                setSelectedGenres([])
                setStep(2)
              }}
              onNext={() => setStep(2)}
            />
          )}

          {step === 2 && (
            <SeedStep
              searchQuery={searchQuery}
              onSearchQueryChange={setSearchQuery}
              suggestions={suggestions}
              noSearchResults={noSearchResults}
              seeds={seeds}
              genreSeeds={genreSeeds}
              loading={loading}
              onAddSeed={addSeed}
              onRemoveSeed={(id) => setSeeds((prev) => prev.filter((item) => item.movie_id !== id))}
              onClearSeeds={() => {
                setSeeds([])
                setSearchQuery("")
                setSuggestions([])
              }}
              onRecommend={() => {
                setStep(3)
                fetchRecommendations(false)
              }}
              onBack={() => setStep(1)}
            />
          )}

          {step === 3 && (
            <ResultsStep
              seeds={seeds}
              selectedGenres={selectedGenres}
              loading={loading}
              ragLoading={ragLoading}
              data={data}
              explain={explain}
              ragExplain={ragExplain}
              resultsJustArrived={resultsJustArrived}
              onShuffle={() => fetchRecommendations(true)}
              onStartOver={resetWizard}
              onBack={() => setStep(2)}
            />
          )}
        </section>
      )}
    </AppShell>
  )
}
