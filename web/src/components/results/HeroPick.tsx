import { useState, type ReactNode } from "react"
import type { RecommendationItem } from "../../types"
import { formatTitle } from "../../utils/format"

const HERO_SCRIM = [
  "linear-gradient(90deg, rgba(19, 27, 24, 0.92) 0%, rgba(19, 27, 24, 0.72) 39%, rgba(19, 27, 24, 0.2) 70%, rgba(19, 27, 24, 0.08) 100%)",
  "linear-gradient(180deg, rgba(19, 27, 24, 0.08), rgba(19, 27, 24, 0.42))",
].join(", ")

type HeroPickProps = {
  item: RecommendationItem
  actions?: ReactNode
}

export function HeroPick({ item, actions }: HeroPickProps) {
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
      <div className="hero-pick-body">
        <span className="hero-rank">#1</span>
        <span className="hero-kicker">Tonight&apos;s strongest match</span>
        <h2 className="hero-title">{formatTitle(item.title)}</h2>
        {actions && <div className="hero-actions">{actions}</div>}
      </div>
    </article>
  )
}
