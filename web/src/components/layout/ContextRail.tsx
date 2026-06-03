import type { ReactNode } from "react"
import type { MovieSuggestion } from "../../types"
import { formatTitle } from "../../utils/format"
import { MovieThumb } from "../ui/MovieThumb"

type ContextRailProps = {
  seeds: MovieSuggestion[]
  emptyHint?: string
  onRemoveSeed?: (movieId: number) => void
  children?: ReactNode
}

/** Persistent left rail: optional filter block (step 3) plus the user's seed picks. */
export function ContextRail({ seeds, emptyHint, onRemoveSeed, children }: ContextRailProps) {
  return (
    <aside className="context-rail" aria-label="Your selections">
      {children}

      <section className="rail-section rail-seeds" aria-label="Your picks">
        <h2 className="rail-title">Your picks</h2>
        {seeds.length === 0 ? (
          <p className="rail-empty">{emptyHint ?? "No movies selected yet."}</p>
        ) : (
          <ul className="seed-list">
            {seeds.map((seed) => (
              <li className="seed-item" key={seed.movie_id}>
                {seed.poster_thumb_url ? (
                  <MovieThumb url={seed.poster_thumb_url} />
                ) : (
                  <span className="seed-thumb-fallback" aria-hidden="true" />
                )}
                <span className="seed-item-title">{formatTitle(seed.title)}</span>
                {onRemoveSeed && (
                  <button
                    type="button"
                    className="seed-remove"
                    aria-label={`Remove ${formatTitle(seed.title)}`}
                    onClick={() => onRemoveSeed(seed.movie_id)}
                  >
                    ×
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  )
}
