import { useEffect, useState } from "react"
import type { KeyboardEvent } from "react"
import { MAX_SEEDS } from "../../config"
import type { MovieSuggestion } from "../../types"
import { formatTitle } from "../../utils/format"
import { MovieThumb } from "../ui/MovieThumb"

type SeedStepProps = {
  searchQuery: string
  onSearchQueryChange: (value: string) => void
  suggestions: MovieSuggestion[]
  noSearchResults: boolean
  seeds: MovieSuggestion[]
  genreSeeds: MovieSuggestion[]
  loading: boolean
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
  seeds,
  genreSeeds,
  loading,
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
    <div className="card">
      <h2>Select Movies</h2>
      <div className="subtitle">Pick 1–{MAX_SEEDS} seed movies</div>
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
            aria-activedescendant={
              suggestionIndex >= 0 ? `suggestion-${suggestions[suggestionIndex]?.movie_id}` : undefined
            }
            autoComplete="off"
          />
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
          {noSearchResults && searchQuery.trim() && (
            <div className="no-results" role="status" aria-live="polite">
              No movies found for &ldquo;{searchQuery.trim()}&rdquo;
            </div>
          )}
        </div>
        <button type="button" onClick={onRecommend} disabled={loading || seeds.length === 0 || seeds.length > MAX_SEEDS}>
          Recommend
        </button>
      </div>
      <div className="seeds">
        <span className="subtle">Selected ({seeds.length}/{MAX_SEEDS}):</span>
        {seeds.length === 0 && (
          <span className="seeds-empty">Search for a movie above, or select one from the list below.</span>
        )}
        {seeds.length >= MAX_SEEDS && (
          <span className="seed-cap-notice">Maximum reached — remove a movie to add another.</span>
        )}
        {seeds.map((seed) => (
          <span className={`seed${seed.poster_thumb_url ? " with-thumb" : ""}`} key={seed.movie_id}>
            {seed.poster_thumb_url && <MovieThumb url={seed.poster_thumb_url} />}
            <span>{formatTitle(seed.title)}</span>
            <button
              type="button"
              onClick={() => onRemoveSeed(seed.movie_id)}
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
      </div>
      <div className="wizard-nav">
        <button type="button" className="ghost" onClick={onBack}>
          Back
        </button>
        <button type="button" className="ghost" onClick={onClearSeeds}>
          Clear selection
        </button>
      </div>
    </div>
  )
}
