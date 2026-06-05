import type { RagChatContext } from "../../types"

function formatYearLabel(yearMin: number | null, yearMax: number | null): string | null {
  if (yearMin != null && yearMax != null) {
    if (yearMin === yearMax) {
      return `Year: ${yearMin}`
    }
    return `Year: ${yearMin}–${yearMax}`
  }
  if (yearMin != null) {
    return `Year: ${yearMin}+`
  }
  if (yearMax != null) {
    return `Before ${yearMax}`
  }
  return null
}

type ContextChipsProps = {
  context: RagChatContext
  disabled?: boolean
  showHeading?: boolean
  onRemoveSeed: (movieId: number, title: string) => void
  onRemoveGenre: (genre: string) => void
  onRemoveYear: () => void
}

export function ContextChips({
  context,
  disabled = false,
  showHeading = true,
  onRemoveSeed,
  onRemoveGenre,
  onRemoveYear,
}: ContextChipsProps) {
  const yearLabel = formatYearLabel(context.year_min, context.year_max)
  const hasAny =
    context.seeds.length > 0 || context.genres.length > 0 || yearLabel != null

  if (!hasAny) {
    return null
  }

  return (
    <div className="context-chips">
      {showHeading && <span className="context-chips-label">Current taste</span>}
      <div className="context-chips-row">
        {context.seeds.map((seed) => (
          <button
            key={`seed-${seed.movie_id}`}
            type="button"
            className="context-chip"
            disabled={disabled}
            onClick={() => onRemoveSeed(seed.movie_id, seed.title)}
          >
            {seed.title}
            <span aria-hidden="true"> ×</span>
          </button>
        ))}
        {context.genres.map((genre) => (
          <button
            key={`genre-${genre}`}
            type="button"
            className="context-chip context-chip--genre"
            disabled={disabled}
            onClick={() => onRemoveGenre(genre)}
          >
            {genre}
            <span aria-hidden="true"> ×</span>
          </button>
        ))}
        {yearLabel && (
          <button
            type="button"
            className="context-chip context-chip--year"
            disabled={disabled}
            onClick={onRemoveYear}
          >
            {yearLabel}
            <span aria-hidden="true"> ×</span>
          </button>
        )}
      </div>
    </div>
  )
}
