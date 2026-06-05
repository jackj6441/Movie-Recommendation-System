import type { RagChatContext } from "../../types"
import { ContextChips } from "./ContextChips"

type TasteRailProps = {
  context: RagChatContext
  disabled?: boolean
  className?: string
  onRemoveSeed: (movieId: number, title: string) => void
  onRemoveGenre: (genre: string) => void
  onRemoveYear: () => void
}

export function TasteRail({
  context,
  disabled = false,
  className = "",
  onRemoveSeed,
  onRemoveGenre,
  onRemoveYear,
}: TasteRailProps) {
  return (
    <aside
      className={`taste-rail ${className}`.trim()}
      aria-label="Current taste"
    >
      <ContextChips
        context={context}
        disabled={disabled}
        showHeading={false}
        onRemoveSeed={onRemoveSeed}
        onRemoveGenre={onRemoveGenre}
        onRemoveYear={onRemoveYear}
      />
    </aside>
  )
}
