import { useId } from "react"
import type { RagChatContext } from "../../types"
import { TasteRailPanel } from "./TasteRailPanel"

type TasteRailCompactProps = {
  context: RagChatContext
  disabled?: boolean
  defaultOpen?: boolean
  availableGenres: string[]
  genresLoading?: boolean
  onRemoveSeed: (movieId: number, title: string) => void
  onRemoveGenre: (genre: string) => void
  onToggleGenre: (genre: string) => void
  onSetYearRange: (min: number, max: number) => void
  onSetAnyYear: () => void
}

export function TasteRailCompact({
  context,
  disabled = false,
  defaultOpen = false,
  availableGenres,
  genresLoading = false,
  onRemoveSeed,
  onRemoveGenre,
  onToggleGenre,
  onSetYearRange,
  onSetAnyYear,
}: TasteRailCompactProps) {
  const summaryId = useId()

  return (
    <details className="taste-rail-compact" open={defaultOpen || undefined}>
      <summary id={summaryId} className="taste-rail-compact-summary">
        Current taste
      </summary>
      <div className="taste-rail-compact-body" aria-labelledby={summaryId}>
        <TasteRailPanel
          context={context}
          availableGenres={availableGenres}
          genresLoading={genresLoading}
          disabled={disabled}
          onRemoveSeed={onRemoveSeed}
          onRemoveGenre={onRemoveGenre}
          onToggleGenre={onToggleGenre}
          onSetYearRange={onSetYearRange}
          onSetAnyYear={onSetAnyYear}
        />
      </div>
    </details>
  )
}
