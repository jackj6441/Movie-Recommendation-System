import { useState } from "react"
import type { RecommendationItem } from "../../types"
import { PosterTile } from "../results/PosterTile"

const STRIP_VISIBLE = 5

type MoreMoviesStripProps = {
  items: RecommendationItem[]
}

export function MoreMoviesStrip({ items }: MoreMoviesStripProps) {
  const [expanded, setExpanded] = useState(false)
  const hiddenCount = Math.max(0, items.length - STRIP_VISIBLE)
  const showToggle = hiddenCount > 0
  const visibleItems = expanded ? items : items.slice(0, STRIP_VISIBLE)

  return (
    <section className="more-movies-section" aria-label="More movies you might like">
      <div className="more-movies-section-head">
        <h3 className="subsection-title">More movies you might like</h3>
        {showToggle && (
          <button
            type="button"
            className="more-movies-toggle"
            onClick={() => setExpanded((value) => !value)}
          >
            {expanded ? "Show fewer" : `Show all (${hiddenCount})`}
          </button>
        )}
      </div>
      <div
        className={`more-movies-strip-wrap${expanded ? " is-expanded" : ""}${hiddenCount > 0 ? " has-overflow" : ""}`}
      >
        <div
          className={`more-movies-strip${expanded ? " more-movies-strip--scroll" : ""}`}
          role="list"
        >
          {visibleItems.map((item, index) => (
            <div key={item.movie_id} role="listitem" className="more-movies-strip-item">
              <PosterTile item={item} rank={index + 2} variant="strip" />
            </div>
          ))}
        </div>
        {(hiddenCount > 0 || expanded) && (
          <div className="more-movies-strip-fade" aria-hidden="true" />
        )}
      </div>
    </section>
  )
}
