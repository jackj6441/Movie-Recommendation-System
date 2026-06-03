import type { ExplainResponse, MovieSuggestion, RagExplanationResponse, RecommendationResponse } from "../../types"
import { formatTitle } from "../../utils/format"
import { FeaturedMovieCard } from "./FeaturedMovieCard"
import { ScoreBreakdown } from "./ScoreBreakdown"
import { MovieThumb } from "../ui/MovieThumb"

type ResultsStepProps = {
  seeds: MovieSuggestion[]
  selectedGenres: string[]
  loading: boolean
  ragLoading: boolean
  data: RecommendationResponse | null
  explain: ExplainResponse | null
  ragExplain: RagExplanationResponse | null
  resultsJustArrived: boolean
  onShuffle: () => void
  onStartOver: () => void
  onBack: () => void
}

export function ResultsStep({
  seeds,
  selectedGenres,
  loading,
  ragLoading,
  data,
  explain,
  ragExplain,
  resultsJustArrived,
  onShuffle,
  onStartOver,
  onBack,
}: ResultsStepProps) {
  return (
    <>
      <div className="seed-banner">
        <span className="seed-banner-label">Seeds:</span>
        {seeds.map((seed) => (
          <span className={`seed${seed.poster_thumb_url ? " with-thumb" : ""}`} key={seed.movie_id}>
            {seed.poster_thumb_url && <MovieThumb url={seed.poster_thumb_url} />}
            <span>{formatTitle(seed.title)}</span>
          </span>
        ))}
        {selectedGenres.length > 0 && (
          <span style={{ color: "#6a655f", marginLeft: "0.25rem" }}>· {selectedGenres.join(", ")}</span>
        )}
      </div>

      <div className={`card full-width${resultsJustArrived ? " arrived" : ""}`}>
        <h2>Featured for you</h2>
        <div className="subtitle">
          {loading && !data ? "Finding your movies…" : `Your top ${Math.min(data?.items.length ?? 0, 3)} picks`}
        </div>
        <div className="featured-grid">
          {loading && !data
            ? [0, 1, 2].map((i) => (
                <div className="movie-card skeleton-card" key={i} aria-hidden="true">
                  <div className="skeleton-dark skeleton-movie-title" />
                  <div className="skeleton-dark skeleton-text-dark" style={{ width: "85%" }} />
                  <div className="skeleton-dark skeleton-text-dark" style={{ width: "60%" }} />
                </div>
              ))
            : data?.items.slice(0, 3).map((recommendation, index) => {
                const ragItem = ragExplain?.items?.find((item) => item.movie_id === recommendation.movie_id)
                return (
                  <FeaturedMovieCard
                    key={recommendation.movie_id}
                    recommendation={recommendation}
                    ragItem={ragItem}
                    index={index}
                  />
                )
              })}
        </div>
        <div className="wizard-nav">
          <button type="button" onClick={onShuffle} disabled={loading || ragLoading}>
            {loading ? "Shuffling…" : "Shuffle"}
          </button>
          <button type="button" className="ghost" onClick={onStartOver}>
            Start over
          </button>
          <button type="button" className="ghost" onClick={onBack}>
            Back
          </button>
        </div>
      </div>

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

      <details className="disclosure">
        <summary>Score breakdown</summary>
        <div className="disclosure-body">
          <p className="subtle" style={{ marginBottom: "1rem" }}>
            How the hybrid model ranked your recommendations.
          </p>
          {explain?.anchor_movie && (
            <p className="subtle" style={{ marginBottom: "0.75rem" }}>
              Anchored on <strong>{formatTitle(explain.anchor_movie.title)}</strong>
            </p>
          )}
          {!explain?.content_available && (
            <p className="warning">Content embeddings unavailable — scores are based on collaborative filtering only.</p>
          )}
          <ScoreBreakdown explain={explain} />
        </div>
      </details>
    </>
  )
}
