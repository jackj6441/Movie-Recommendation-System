import type { MovieSuggestion, RagExplanationResponse, RecommendationResponse } from "../../types"
import type { TimeRangeKey } from "../../config"
import { HeroPick } from "./HeroPick"
import { PosterTile } from "./PosterTile"
import { ResultsRail } from "./ResultsRail"
import { WizardShell } from "../layout/WizardShell"

type ResultsStepProps = {
  seeds: MovieSuggestion[]
  genres: string[]
  resultTopics: string[]
  timeRange: TimeRangeKey
  loading: boolean
  shuffling: boolean
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

const SKELETON_TILES = Array.from({ length: 8 })

export function ResultsStep({
  seeds,
  genres,
  resultTopics,
  timeRange,
  loading,
  shuffling,
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
  const initialLoading = loading && !data
  const refetching = loading && Boolean(data) && !shuffling
  const noMatches = Boolean(data) && !loading && !hasResults

  const hero = items[0]
  const heroRag = hero ? ragExplain?.items?.find((item) => item.movie_id === hero.movie_id) : undefined
  const rest = items.slice(1)

  const statusMessage = initialLoading
    ? "Finding your movies."
    : shuffling && loading
      ? "Shuffling recommendations."
      : refetching
        ? "Updating recommendations."
        : noMatches
          ? "No movies match your current filters."
          : hasResults
            ? `Showing ${items.length} recommendations.`
            : ""

  const shuffleLabel = shuffling && loading ? "Shuffling…" : "Shuffle"

  return (
    <WizardShell
      rail={
        <ResultsRail
          seeds={seeds}
          genres={genres}
          resultTopics={resultTopics}
          timeRange={timeRange}
          disabled={loading}
          onToggleTopic={onToggleTopic}
          onChangeTimeRange={onChangeTimeRange}
          onResetFilters={onResetFilters}
        />
      }
    >
      <div className="results-main">
        <p className="sr-only" role="status" aria-live="polite">
          {statusMessage}
        </p>

        <header className="results-header">
          <h2 className="section-title">Featured for you</h2>
          {!initialLoading && hasResults && (
            <p className="results-meta">{items.length} matches</p>
          )}
        </header>

        <div
          className={`results-stage${refetching ? " is-refetching" : ""}${resultsJustArrived ? " arrived" : ""}`}
          aria-busy={loading}
        >
          {initialLoading ? (
            <>
              <div className="hero-pick hero-skeleton" aria-hidden="true" />
              <h3 className="subsection-title">More movies you might like</h3>
              <div className="more-movies-grid">
                {SKELETON_TILES.map((_, index) => (
                  <div className="poster-tile poster-skeleton" key={index} aria-hidden="true" />
                ))}
              </div>
            </>
          ) : noMatches ? (
            <div className="empty-results" role="status">
              <p>No movies match your current filters. Try a wider decade or fewer genres.</p>
              <button type="button" className="retry-btn" onClick={onResetFilters}>
                Reset filters
              </button>
            </div>
          ) : hasResults ? (
            <>
              <HeroPick item={hero} ragItem={heroRag} ragLoading={ragLoading} />

              {rest.length > 0 && (
                <>
                  <h3 className="subsection-title">More movies you might like</h3>
                  <div className="more-movies-grid">
                    {rest.map((item, index) => (
                      <PosterTile
                        key={item.movie_id}
                        item={item}
                        rank={index < 2 ? index + 2 : undefined}
                      />
                    ))}
                  </div>
                </>
              )}
            </>
          ) : null}

          {refetching && (
            <div className="refetch-veil" aria-hidden="true">
              <span className="refetch-dot" />
              Updating
            </div>
          )}
        </div>

        <nav className="wizard-nav" aria-label="Recommendation actions">
          <button type="button" onClick={onShuffle} disabled={loading || ragLoading}>
            {shuffleLabel}
          </button>
          <button type="button" className="ghost" onClick={onStartOver}>
            Start over
          </button>
          <button type="button" className="ghost" onClick={onBack}>
            Back
          </button>
        </nav>
      </div>
    </WizardShell>
  )
}
