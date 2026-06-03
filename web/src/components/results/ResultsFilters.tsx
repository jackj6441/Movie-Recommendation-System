import { TIME_RANGES, type TimeRangeKey } from "../../config"

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
  const hasActiveFilters = resultTopics.length > 0 || timeRange !== "all"

  return (
    <div className="results-filters card full-width">
      <div className="results-filters-head">
        <h2>Refine results</h2>
        {hasActiveFilters && (
          <button type="button" className="ghost reset-filters-btn" onClick={onResetFilters} disabled={disabled}>
            Reset filters
          </button>
        )}
      </div>

      <div className="filter-group">
        <span className="filter-label" id="time-range-label">
          Time range
        </span>
        <div className="chips" role="group" aria-labelledby="time-range-label">
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
          <span className="filter-label" id="topic-label">
            Topics
          </span>
          <div className="chips" role="group" aria-labelledby="topic-label">
            {genres.map((genre) => (
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
        </div>
      )}
    </div>
  )
}
