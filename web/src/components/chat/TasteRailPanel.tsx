import { useEffect, useState, type ReactNode } from "react"
import type { RagChatContext } from "../../types"
import {
  contextToSlider,
  formatYearSummary,
  isAnyYear,
  sliderMatchesContext,
} from "../../lib/tasteYear"
import { CloseIcon } from "../icons"
import { GenreChipsRow } from "./GenreChipsRow"
import { YearRangeSlider } from "./YearRangeSlider"

type OpenSection = "genres" | "year" | null

type TasteRailPanelProps = {
  context: RagChatContext
  availableGenres: string[]
  genresLoading?: boolean
  disabled?: boolean
  onRemoveSeed: (movieId: number, title: string) => void
  onRemoveGenre: (genre: string) => void
  onToggleGenre: (genre: string) => void
  onSetYearRange: (min: number, max: number) => void
  onSetAnyYear: () => void
}

function TastePill({
  children,
  selected = true,
  muted = false,
  onRemove,
  disabled,
}: {
  children: ReactNode
  selected?: boolean
  muted?: boolean
  onRemove?: () => void
  disabled?: boolean
}) {
  if (muted) {
    return <span className="taste-pill taste-pill--muted">{children}</span>
  }
  if (onRemove) {
    return (
      <button
        type="button"
        className={`taste-pill${selected ? " taste-pill--selected" : ""}`}
        disabled={disabled}
        onClick={onRemove}
      >
        {children}
        <CloseIcon className="taste-pill__close" size={14} />
      </button>
    )
  }
  return (
    <span className={`taste-pill${selected ? " taste-pill--selected" : ""}`}>
      {children}
    </span>
  )
}

export function TasteRailPanel({
  context,
  availableGenres,
  genresLoading = false,
  disabled = false,
  onRemoveSeed,
  onRemoveGenre,
  onToggleGenre,
  onSetYearRange,
  onSetAnyYear,
}: TasteRailPanelProps) {
  const [openSection, setOpenSection] = useState<OpenSection>(null)
  const [previewRange, setPreviewRange] = useState(() => contextToSlider(context))

  useEffect(() => {
    setPreviewRange(contextToSlider(context))
  }, [context])

  const toggleSection = (section: "genres" | "year") => {
    setOpenSection((prev) => (prev === section ? null : section))
  }

  const anyYear = isAnyYear(context)
  const previewAnyYear = previewRange.anyYear
  const yearSummary = formatYearSummary(context)
  const yearDraftPending =
    openSection === "year" && !sliderMatchesContext(previewRange, context)

  return (
    <div className="taste-rail-panel">
      <section className="taste-rail-section">
        <div className="taste-rail-section-head">
          <h3 className="taste-rail-section-title">Genres</h3>
          <button
            type="button"
            className="taste-rail-edit"
            disabled={disabled}
            onClick={() => toggleSection("genres")}
          >
            Edit
          </button>
        </div>
        {openSection === "genres" ? (
          <GenreChipsRow
            genres={availableGenres}
            selected={context.genres}
            loading={genresLoading}
            disabled={disabled}
            ariaLabel="Edit genres for this chat"
            onToggle={onToggleGenre}
          />
        ) : (
          <div className="taste-rail-pill-row">
            {context.genres.length === 0 ? (
              <TastePill muted>None yet</TastePill>
            ) : (
              context.genres.map((genre) => (
                <TastePill
                  key={genre}
                  disabled={disabled}
                  onRemove={() => onRemoveGenre(genre)}
                >
                  {genre}
                </TastePill>
              ))
            )}
          </div>
        )}
      </section>

      <section className="taste-rail-section">
        <div className="taste-rail-section-head">
          <h3 className="taste-rail-section-title">Release year</h3>
          <button
            type="button"
            className="taste-rail-edit"
            disabled={disabled}
            onClick={() => toggleSection("year")}
          >
            Edit
          </button>
        </div>
        {openSection === "year" ? (
          <div className="taste-rail-year-editor">
            <p className="taste-rail-year-committed">
              Applied: <strong>{yearSummary}</strong>
            </p>
            {yearDraftPending && (
              <p className="taste-rail-year-draft" role="status">
                Release the slider to apply your new range.
              </p>
            )}
            <div className="taste-rail-pill-row">
              <button
                type="button"
                className={`taste-pill${previewAnyYear ? " taste-pill--selected" : ""}`}
                disabled={disabled}
                aria-pressed={previewAnyYear}
                onClick={() => onSetAnyYear()}
              >
                Any year
              </button>
            </div>
            <YearRangeSlider
              min={previewRange.min}
              max={previewRange.max}
              disabled={disabled}
              onChange={(min, max) => setPreviewRange({ min, max, anyYear: false })}
              onCommit={(min, max) => {
                onSetYearRange(min, max)
                setOpenSection(null)
              }}
            />
          </div>
        ) : (
          <div className="taste-rail-pill-row">
            <TastePill
              disabled={disabled}
              onRemove={anyYear ? undefined : () => onSetAnyYear()}
            >
              {yearSummary}
            </TastePill>
          </div>
        )}
      </section>

      <section className="taste-rail-section">
        <div className="taste-rail-section-head">
          <h3 className="taste-rail-section-title">Starting movies</h3>
        </div>
        <div className="taste-rail-pill-row">
          {context.seeds.length === 0 ? (
            <TastePill muted>None yet</TastePill>
          ) : (
            context.seeds.map((seed) => (
              <TastePill
                key={seed.movie_id}
                disabled={disabled}
                onRemove={() => onRemoveSeed(seed.movie_id, seed.title)}
              >
                {seed.title}
              </TastePill>
            ))
          )}
        </div>
      </section>
    </div>
  )
}
