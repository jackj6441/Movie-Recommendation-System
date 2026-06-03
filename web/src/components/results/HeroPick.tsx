import { useState } from "react"
import type { RagExplanationItem, RecommendationItem } from "../../types"
import { formatTitle } from "../../utils/format"

// Keeps poster text readable without dimming the whole movie artwork.
const HERO_SCRIM =
  "linear-gradient(180deg, rgba(20,18,16,0.05), rgba(20,18,16,0.72))"

type HeroPickProps = {
  item: RecommendationItem
  ragItem?: RagExplanationItem
  ragLoading: boolean
}

export function HeroPick({ item, ragItem, ragLoading }: HeroPickProps) {
  const [posterHidden, setPosterHidden] = useState(false)
  const showPoster = Boolean(item.poster_url) && !posterHidden

  return (
    <article className={`hero-pick${showPoster ? " has-poster" : ""}`}>
      {item.poster_url && (
        <img
          className="hero-pick-probe"
          src={item.poster_url}
          alt=""
          onError={() => setPosterHidden(true)}
        />
      )}
      <div
        className="hero-poster-panel"
        style={
          showPoster
            ? { backgroundImage: `${HERO_SCRIM}, url(${item.poster_url})` }
            : undefined
        }
        aria-hidden="true"
      >
        <span className="hero-rank">#1</span>
      </div>
      <div className="hero-pick-body">
        <span className="hero-kicker">Tonight&apos;s strongest match</span>
        <h2 className="hero-title">{formatTitle(item.title)}</h2>
        {ragItem ? (
          <div className="hero-reason-block">
            <span>Why it fits</span>
            <p className="hero-reason">{ragItem.reason}</p>
          </div>
        ) : ragLoading ? (
          <div className="hero-reason-skeleton" aria-hidden="true">
            <span className="skeleton-dark hero-reason-line" />
            <span className="skeleton-dark hero-reason-line short" />
          </div>
        ) : null}
      </div>
    </article>
  )
}
