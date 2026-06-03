import type { MovieSuggestion, RagExplanationResponse, RecommendationResponse } from "../../types"
import type { TimeRangeKey } from "../../config"
import { formatTitle } from "../../utils/format"
import { FeaturedMovieCard } from "./FeaturedMovieCard"
import { PosterTile } from "./PosterTile"
import { ResultsFilters } from "./ResultsFilters"
import { MovieThumb } from "../ui/MovieThumb"

type ResultsStepProps = {
  seeds: MovieSuggestion[]
  genres: string[]
  resultTopics: string[]
  timeRange: TimeRangeKey
  loading: boolean
  ragLoading: boolean
  data: RecommendationResponse | null
  ragExplain: RagExplanationResponse | null
  resultsJustArrived: boolean
  onToggleTopic: (genre: string) => void
  onChangeTimeRange: (key: TimeRangeKey) => void
  onResetFilters: () => void
  onShuffle: () => void
  onStartOver: () => void
  onBack: () => void
}

export function ResultsStep({
  seeds,
  genres,
  resultTopics,
  timeRange,
  loading,
  ragLoading,
  data,
  ragExplain,
  resultsJustArrived,
  onToggleTopic,
  onChangeTimeRange,
  onResetFilters,
  onShuffle,
  onStartOver,
  onBack,
}: ResultsStepProps) {
  const items = data?.items ?? []
  const hasResults = items.length > 0
  const noMatches = Boolean(data) && !loading && !hasResults

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
      </div>

      <ResultsFilters
        genres={genres}
        resultTopics={resultTopics}
        timeRange={timeRange}
        disabled={loading}
        onToggleTopic={onToggleTopic}
        onChangeTimeRange={onChangeTimeRange}
        onResetFilters={onResetFilters}
      />

      <div className={`card full-width${resultsJustArrived ? " arrived" : ""}`}>
        <h2>Featured for you</h2>
        <div className="subtitle">
          {loading && !data
            ? "Finding your movies…"
            : noMatches
              ? "No matches for these filters"
              : `Your top ${Math.min(items.length, 3)} picks`}
        </div>

        {noMatches ? (
          <div className="empty-results" role="status">
            <p>No movies match your current filters.</p>
            <button type="button" className="retry-btn" onClick={onResetFilters}>
              Reset filters
            </button>
          </div>
        ) : (
          <div className="featured-grid">
            {loading && !data
              ? [0, 1, 2].map((i) => (
                  <div className="movie-card skeleton-card" key={i} aria-hidden="true">
                    <div className="skeleton-dark skeleton-movie-title" />
                    <div className="skeleton-dark skeleton-text-dark" style={{ width: "85%" }} />
                    <div className="skeleton-dark skeleton-text-dark" style={{ width: "60%" }} />
                  </div>
                ))
              : items.slice(0, 3).map((recommendation, index) => {
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
        )}

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

      {items.length > 3 && (
        <div className="card full-width">
          <h2>More movies you might like</h2>
          <div className="subtitle">More matches ranked by the same model.</div>
          <div className="more-movies-grid">
            {items.slice(3).map((item) => (
              <PosterTile key={item.movie_id} item={item} />
            ))}
          </div>
        </div>
      )}
    </>
  )
}
