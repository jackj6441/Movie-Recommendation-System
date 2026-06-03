import { MAX_GENRES } from "../../config"

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
  return (
    <div className="card">
      <h2>Select Genres</h2>
      <div className="subtitle">Choose up to {MAX_GENRES} genres to narrow your seeds (optional)</div>

      {loading && (
        <div className="chips" aria-busy="true" aria-label="Loading genres">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <span className="chip skeleton" key={i} style={{ width: "5rem", height: "2rem" }} />
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
            {genres.map((genre) => (
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
          <p className="genre-status">
            {selectedGenres.length}/{MAX_GENRES} selected
            {selectedGenres.length >= MAX_GENRES && " — remove one to pick another"}
          </p>
        </>
      )}

      <div className="wizard-nav">
        <button type="button" className="ghost" onClick={onSkip}>
          Skip
        </button>
        <button type="button" onClick={onNext}>
          Next
        </button>
      </div>
    </div>
  )
}
