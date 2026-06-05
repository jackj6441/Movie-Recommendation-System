import { useId } from "react"
import type { RagChatContext } from "../../types"
import { ContextChips } from "./ContextChips"

type TasteRailCompactProps = {
  context: RagChatContext
  disabled?: boolean
  onRemoveSeed: (movieId: number, title: string) => void
  onRemoveGenre: (genre: string) => void
  onRemoveYear: () => void
}

export function TasteRailCompact({
  context,
  disabled = false,
  onRemoveSeed,
  onRemoveGenre,
  onRemoveYear,
}: TasteRailCompactProps) {
  const summaryId = useId()

  return (
    <details className="taste-rail-compact">
      <summary id={summaryId} className="taste-rail-compact-summary">
        Current taste
      </summary>
      <div className="taste-rail-compact-body" aria-labelledby={summaryId}>
        <ContextChips
          context={context}
          disabled={disabled}
          showHeading={false}
          onRemoveSeed={onRemoveSeed}
          onRemoveGenre={onRemoveGenre}
          onRemoveYear={onRemoveYear}
        />
      </div>
    </details>
  )
}
