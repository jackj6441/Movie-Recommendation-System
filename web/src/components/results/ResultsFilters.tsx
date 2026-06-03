import { useState } from "react"
import { TIME_RANGES, type TimeRangeKey } from "../../config"

const VISIBLE_GENRES = 6

type ResultsFiltersProps = {
  genres: string[]
  resultTopics: string[]
  timeRange: TimeRangeKey
  disabled: boolean
  onToggleTopic: (genre: string) => void
  onChangeTimeRange: (key: TimeRangeKey) => void
  onResetFilters: () => void
}

export function ResultsFilters({
  genres,
  resultTopics,
  timeRange,
  disabled,
  onToggleTopic,
  onChangeTimeRange,
  onResetFilters,
}: ResultsFiltersProps) {
  const [showAllGenres, setShowAllGenres] = useState(false)
  const hasActiveFilters = resultTopics.length > 0 || timeRange !== "all"

  const orderedGenres = [
    ...genres.filter((genre) => resultTopics.includes(genre)),
    ...genres.filter((genre) => !resultTopics.includes(genre)),
  ]
  const visibleGenres = showAllGenres ? orderedGenres : orderedGenres.slice(0, VISIBLE_GENRES)
  const hiddenCount = orderedGenres.length - visibleGenres.length

  return (
    <section className="rail-section rail-filters" aria-label="Active filters">
      <div className="rail-head">
        <h2 className="rail-title">Active filters</h2>
        {hasActiveFilters && (
          <button type="button" className="rail-reset" onClick={onResetFilters} disabled={disabled}>
            Reset
          </button>
        )}
      </div>

      <div className="filter-group">
        <span className="filter-label" id="time-range-label">
          Decade
        </span>
        <div className="chips chips-compact" role="group" aria-labelledby="time-range-label">
          {TIME_RANGES.map((range) => (
            <button
              type="button"
              key={range.key}
              className={`chip ${timeRange === range.key ? "active" : ""}`}
              aria-pressed={timeRange === range.key}
              disabled={disabled}
              onClick={() => onChangeTimeRange(range.key)}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      {genres.length > 0 && (
        <div className="filter-group">
          <span className="filter-label" id="results-genre-label">
            Genres
          </span>
          <div className="chips chips-compact" role="group" aria-labelledby="results-genre-label">
            {visibleGenres.map((genre) => (
              <button
                type="button"
                key={genre}
                className={`chip ${resultTopics.includes(genre) ? "active" : ""}`}
                aria-pressed={resultTopics.includes(genre)}
                disabled={disabled}
                onClick={() => onToggleTopic(genre)}
              >
                {genre}
              </button>
            ))}
          </div>
          {hiddenCount > 0 && !showAllGenres && (
            <button type="button" className="chip-more" onClick={() => setShowAllGenres(true)}>
              {`+ ${hiddenCount} more`}
            </button>
          )}
          {showAllGenres && orderedGenres.length > VISIBLE_GENRES && (
            <button type="button" className="chip-more" onClick={() => setShowAllGenres(false)}>
              Show fewer
            </button>
          )}
        </div>
      )}
    </section>
  )
}
