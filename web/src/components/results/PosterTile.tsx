import { useState } from "react"
import type { RecommendationItem } from "../../types"
import { formatTitle } from "../../utils/format"

const POSTER_OVERLAY = "linear-gradient(180deg, rgba(20, 18, 16, 0.05), rgba(20, 18, 16, 0.85))"

type PosterTileProps = {
  item: RecommendationItem
  rank?: number
  variant?: "default" | "strip"
  onAddSeed?: () => void
  addSeedDisabled?: boolean
  isInSeeds?: boolean
  seedSetFull?: boolean
}

export function PosterTile({
  item,
  rank,
  variant = "default",
  onAddSeed,
  addSeedDisabled = false,
  isInSeeds = false,
  seedSetFull = false,
}: PosterTileProps) {
  const [posterHidden, setPosterHidden] = useState(false)
  const showPoster = Boolean(item.poster_url) && !posterHidden
  const label = formatTitle(item.title)
  const className = `poster-tile${variant === "strip" ? " poster-tile--strip" : ""}${
    showPoster ? " has-poster" : ""
  }${isInSeeds ? " is-in-seeds" : ""}${onAddSeed && seedSetFull ? " is-at-limit" : ""}${
    onAddSeed ? " poster-tile--interactive" : ""
  }`
  const posterStyle = showPoster
    ? {
        backgroundImage: `${POSTER_OVERLAY}, url(${item.poster_url})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
      }
    : undefined
  const content = (
    <>
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
      <h3 className="poster-tile-title">{label}</h3>
    </>
  )

  if (isInSeeds) {
    return (
      <article
        className={className}
        style={posterStyle}
        aria-label={`${label} is in your starting movies`}
      >
        {content}
      </article>
    )
  }

  if (onAddSeed) {
    const atLimit = seedSetFull
    return (
      <button
        type="button"
        className={className}
        style={posterStyle}
        disabled={addSeedDisabled || atLimit}
        title={atLimit ? "Seed set full (max 5)" : undefined}
        aria-label={`Add ${label} to starting movies`}
        onClick={onAddSeed}
      >
        {content}
      </button>
    )
  }

  return (
    <article className={className} style={posterStyle}>
      {content}
    </article>
  )
}
