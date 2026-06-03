import { useEffect, useState } from "react"
import type { KeyboardEvent } from "react"
import { MAX_SEEDS } from "../../config"
import type { MovieSuggestion } from "../../types"
import { formatTitle } from "../../utils/format"
import { ContextRail } from "../layout/ContextRail"
import { WizardShell } from "../layout/WizardShell"
import { MovieThumb } from "../ui/MovieThumb"

type SeedStepProps = {
  searchQuery: string
  onSearchQueryChange: (value: string) => void
  suggestions: MovieSuggestion[]
  noSearchResults: boolean
  searchLoading: boolean
  searchError: string | null
  seeds: MovieSuggestion[]
  genreSeeds: MovieSuggestion[]
  loading: boolean
  onRetrySearch: () => void
  onAddSeed: (movie: MovieSuggestion) => void
  onRemoveSeed: (movieId: number) => void
  onClearSeeds: () => void
  onRecommend: () => void
  onBack: () => void
}

export function SeedStep({
  searchQuery,
  onSearchQueryChange,
  suggestions,
  noSearchResults,
  searchLoading,
  searchError,
  seeds,
  genreSeeds,
  loading,
  onRetrySearch,
  onAddSeed,
  onRemoveSeed,
  onClearSeeds,
  onRecommend,
  onBack,
}: SeedStepProps) {
  const [suggestionIndex, setSuggestionIndex] = useState(-1)

  useEffect(() => {
    setSuggestionIndex(-1)
  }, [suggestions])

  const handleSearchKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!suggestions.length) return
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setSuggestionIndex((prev) => (prev + 1) % suggestions.length)
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setSuggestionIndex((prev) => (prev <= 0 ? suggestions.length - 1 : prev - 1))
    } else if (e.key === "Enter" && suggestionIndex >= 0) {
      e.preventDefault()
      if (seeds.length >= MAX_SEEDS) return
      onAddSeed(suggestions[suggestionIndex])
    } else if (e.key === "Escape") {
      setSuggestionIndex(-1)
    }
  }

  const tryAddSeed = (movie: MovieSuggestion) => {
    if (seeds.length >= MAX_SEEDS) return
    if (seeds.some((seed) => seed.movie_id === movie.movie_id)) return
    onAddSeed(movie)
  }

  return (
    <WizardShell
      rail={
        <ContextRail
          seeds={seeds}
          emptyHint="Search or select movies in the panel beside you."
          onRemoveSeed={onRemoveSeed}
        />
      }
    >
      <div className="card step-panel">
        <h2 className="section-title">Select movies</h2>
        <p className="step-lead">Pick 1–{MAX_SEEDS} seed movies that capture your taste.</p>

        <div className="controls">
          <div className="search">
            <input
              type="text"
              placeholder="Search movies..."
              value={searchQuery}
              onChange={(event) => onSearchQueryChange(event.target.value)}
              onKeyDown={handleSearchKeyDown}
              role="combobox"
              aria-expanded={suggestions.length > 0}
              aria-autocomplete="list"
              aria-controls="search-suggestions"
              aria-describedby="movie-search-hint"
              aria-activedescendant={
                suggestionIndex >= 0 ? `suggestion-${suggestions[suggestionIndex]?.movie_id}` : undefined
              }
              autoComplete="off"
            />
            <p className="search-hint" id="movie-search-hint">
              Search by title, then select 1–{MAX_SEEDS} movies.
            </p>
            {searchLoading && searchQuery.trim() && (
              <div className="search-feedback" role="status" aria-live="polite">
                Searching movies...
              </div>
            )}
            {suggestions.length > 0 && (
              <div className="suggestions" id="search-suggestions" role="listbox">
                {suggestions.map((movie, idx) => (
                  <button
                    type="button"
                    key={movie.movie_id}
                    id={`suggestion-${movie.movie_id}`}
                    role="option"
                    aria-selected={idx === suggestionIndex}
                    className={idx === suggestionIndex ? "focused" : ""}
                    onClick={() => tryAddSeed(movie)}
                  >
                    {movie.poster_thumb_url && <MovieThumb url={movie.poster_thumb_url} />}
                    <span>{formatTitle(movie.title)}</span>
                  </button>
                ))}
              </div>
            )}
            {searchError && searchQuery.trim() && (
              <div className="search-error" role="alert">
                <span>{searchError}</span>
                <button type="button" className="retry-btn compact" onClick={onRetrySearch}>
                  Retry search
                </button>
              </div>
            )}
            {!searchError && noSearchResults && searchQuery.trim() && (
              <div className="no-results" role="status" aria-live="polite">
                No movies found for &ldquo;{searchQuery.trim()}&rdquo;
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={onRecommend}
            disabled={loading || seeds.length === 0 || seeds.length > MAX_SEEDS}
          >
            Recommend
          </button>
        </div>

        {seeds.length >= MAX_SEEDS && (
          <p className="seed-cap-notice">Maximum reached — remove a pick from the rail to add another.</p>
        )}

        {genreSeeds.length > 0 && (
          <section className="seed-suggestions" aria-label="Suggested seeds">
            <h3 className="subsection-title">Suggested from your genres</h3>
            <div className="list">
              {genreSeeds.map((movie) => (
                <div className={`row${movie.poster_thumb_url ? " with-thumb" : ""}`} key={movie.movie_id}>
                  <div className="row-main">
                    {movie.poster_thumb_url && <MovieThumb url={movie.poster_thumb_url} />}
                    <span>{formatTitle(movie.title)}</span>
                  </div>
                  <button type="button" className="ghost" onClick={() => tryAddSeed(movie)}>
                    Select
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        <nav className="wizard-nav" aria-label="Seed step actions">
          <button type="button" className="ghost" onClick={onBack}>
            Back
          </button>
          <button type="button" className="ghost" onClick={onClearSeeds}>
            Clear selection
          </button>
        </nav>
      </div>
    </WizardShell>
  )
}
