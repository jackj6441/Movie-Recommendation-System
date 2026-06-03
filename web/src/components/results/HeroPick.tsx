import { useState } from "react"
import type { RagExplanationItem, RecommendationItem } from "../../types"
import { formatTitle } from "../../utils/format"

// Scrim is heavy on the left where the text sits and clears toward the right so
// the poster art reads. Applied over the poster via an inline background-image.
const HERO_SCRIM =
  "linear-gradient(90deg, rgba(22,18,15,0.94) 0%, rgba(22,18,15,0.78) 34%, rgba(22,18,15,0.28) 64%, rgba(22,18,15,0) 100%)"

type HeroPickProps = {
  item: RecommendationItem
  ragItem?: RagExplanationItem
  ragLoading: boolean
}

export function HeroPick({ item, ragItem, ragLoading }: HeroPickProps) {
  const [posterHidden, setPosterHidden] = useState(false)
  const showPoster = Boolean(item.poster_url) && !posterHidden

  return (
    <article
      className={`hero-pick${showPoster ? " has-poster" : ""}`}
      style={
        showPoster
          ? { backgroundImage: `${HERO_SCRIM}, url(${item.poster_url})` }
          : undefined
      }
    >
      {item.poster_url && (
        <img
          className="hero-pick-probe"
          src={item.poster_url}
          alt=""
          onError={() => setPosterHidden(true)}
        />
      )}
      <span className="hero-bracket hero-bracket-tl" aria-hidden="true" />
      <span className="hero-bracket hero-bracket-tr" aria-hidden="true" />
      <span className="hero-bracket hero-bracket-bl" aria-hidden="true" />
      <span className="hero-bracket hero-bracket-br" aria-hidden="true" />

      <div className="hero-pick-body">
        <span className="hero-rank">#1</span>
        <h2 className="hero-title">{formatTitle(item.title)}</h2>
        {ragItem ? (
          <p className="hero-reason">{ragItem.reason}</p>
        ) : ragLoading ? (
          <p className="hero-reason-skeleton" aria-hidden="true">
            <span className="skeleton-dark hero-reason-line" />
            <span className="skeleton-dark hero-reason-line short" />
          </p>
        ) : null}
      </div>
    </article>
  )
}
