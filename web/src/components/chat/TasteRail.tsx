import type { RagChatContext } from "../../types"
import { SidebarSceneDecor } from "./SidebarSceneDecor"
import { TasteRailPanel } from "./TasteRailPanel"

type TasteRailProps = {
  context: RagChatContext
  disabled?: boolean
  className?: string
  availableGenres: string[]
  genresLoading?: boolean
  onRemoveSeed: (movieId: number, title: string) => void
  onRemoveGenre: (genre: string) => void
  onToggleGenre: (genre: string) => void
  onSetYearRange: (min: number, max: number) => void
  onSetAnyYear: () => void
}

export function TasteRail({
  context,
  disabled = false,
  className = "",
  availableGenres,
  genresLoading = false,
  onRemoveSeed,
  onRemoveGenre,
  onToggleGenre,
  onSetYearRange,
  onSetAnyYear,
}: TasteRailProps) {
  return (
    <aside
      className={`taste-rail ${className}`.trim()}
      aria-label="Current taste"
    >
      <div className="taste-rail-body">
        <h2 className="taste-rail-title">Current taste</h2>
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
      <SidebarSceneDecor variant="console" />
    </aside>
  )
}
