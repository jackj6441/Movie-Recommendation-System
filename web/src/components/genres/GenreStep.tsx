import { useState } from "react"
import { MAX_GENRES, PRIORITY_GENRES } from "../../config"
import { sortGenres } from "../../utils/format"

const VISIBLE_GENRES = 6

type GenreStepProps = {
  genres: string[]
  loading: boolean
  error: string | null
  selectedGenres: string[]
  onToggleGenre: (genre: string) => void
  onRetry: () => void
  onSkip: () => void
  onNext: () => void
}

export function GenreStep({
  genres,
  loading,
  error,
  selectedGenres,
  onToggleGenre,
  onRetry,
  onSkip,
  onNext,
}: GenreStepProps) {
  const [showAllGenres, setShowAllGenres] = useState(false)

  const orderedGenres = sortGenres(genres, PRIORITY_GENRES)
  const visibleGenres = showAllGenres ? orderedGenres : orderedGenres.slice(0, VISIBLE_GENRES)
  const hiddenCount = orderedGenres.length - visibleGenres.length

  return (
    <div className="card full-width genre-step">
      <h2 className="section-title">Select genres</h2>
      <p className="step-lead">Choose up to {MAX_GENRES} genres to narrow your seeds. Optional.</p>

      {loading && (
        <div className="chips" aria-busy="true" aria-label="Loading genres">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <span className="chip skeleton" key={i} style={{ width: "5rem", height: "2.75rem" }} />
          ))}
        </div>
      )}

      {!loading && error && (
        <div className="genre-error" role="alert">
          <p className="error-text">{error}</p>
          <button type="button" className="retry-btn" onClick={onRetry}>
            Retry
          </button>
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="chips" role="group" aria-label="Movie genres">
            {visibleGenres.map((genre) => (
              <button
                type="button"
                key={genre}
                className={`chip ${selectedGenres.includes(genre) ? "active" : ""}`}
                aria-pressed={selectedGenres.includes(genre)}
                onClick={() => onToggleGenre(genre)}
              >
                {genre}
              </button>
            ))}
          </div>
          {hiddenCount > 0 && !showAllGenres && (
            <button type="button" className="chip-more" onClick={() => setShowAllGenres(true)}>
              {`+ ${hiddenCount} more genres`}
            </button>
          )}
          {showAllGenres && orderedGenres.length > VISIBLE_GENRES && (
            <button type="button" className="chip-more" onClick={() => setShowAllGenres(false)}>
              Show fewer
            </button>
          )}
          <p className="genre-status">
            {selectedGenres.length}/{MAX_GENRES} selected
            {selectedGenres.length >= MAX_GENRES && " — remove one to pick another"}
          </p>
        </>
      )}

      <nav className="wizard-nav" aria-label="Genre step actions">
        <button type="button" className="ghost" onClick={onSkip}>
          Skip
        </button>
        <button type="button" onClick={onNext}>
          Next
        </button>
      </nav>
    </div>
  )
}
