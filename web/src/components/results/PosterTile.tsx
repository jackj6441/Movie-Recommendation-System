import { useState } from "react"
import type { RecommendationItem } from "../../types"
import { formatTitle } from "../../utils/format"

const POSTER_OVERLAY = "linear-gradient(180deg, rgba(20, 18, 16, 0.05), rgba(20, 18, 16, 0.85))"

type PosterTileProps = {
  item: RecommendationItem
  rank?: number
  variant?: "default" | "strip"
}

export function PosterTile({ item, rank, variant = "default" }: PosterTileProps) {
  const [posterHidden, setPosterHidden] = useState(false)
  const showPoster = Boolean(item.poster_url) && !posterHidden

  return (
    <article
      className={`poster-tile${variant === "strip" ? " poster-tile--strip" : ""}${showPoster ? " has-poster" : ""}`}
      style={
        showPoster
          ? {
              backgroundImage: `${POSTER_OVERLAY}, url(${item.poster_url})`,
              backgroundSize: "cover",
              backgroundPosition: "center",
            }
          : undefined
      }
    >
      {item.poster_url && (
        <img
          className="poster-tile-probe"
          src={item.poster_url}
          alt=""
          loading="lazy"
          decoding="async"
          onError={() => setPosterHidden(true)}
        />
      )}
      {rank != null && <span className="poster-rank">{`#${rank}`}</span>}
      <h3 className="poster-tile-title">{formatTitle(item.title)}</h3>
    </article>
  )
}
