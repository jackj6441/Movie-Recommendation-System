import { useState } from "react"
import type { RecommendationItem } from "../../types"
import { formatTitle } from "../../utils/format"
import { PosterFrame } from "./PosterFrame"

type PosterTileProps = {
  item: RecommendationItem
  rank?: number
  variant?: "default" | "strip"
  /** Strip layout: render frame only (caption rendered by parent row). */
  frameOnly?: boolean
  onAddSeed?: () => void
  addSeedDisabled?: boolean
  isInSeeds?: boolean
  seedSetFull?: boolean
}

function PosterArt({
  showPoster,
  posterUrl,
  onPosterError,
}: {
  showPoster: boolean
  posterUrl?: string
  onPosterError: () => void
}) {
  if (showPoster && posterUrl) {
    return (
      <img
        className="poster-frame__art"
        src={posterUrl}
        alt=""
        loading="lazy"
        decoding="async"
        onError={onPosterError}
      />
    )
  }
  return <div className="poster-frame__fallback" aria-hidden="true" />
}

export function PosterTile({
  item,
  rank,
  variant = "default",
  frameOnly = false,
  onAddSeed,
  addSeedDisabled = false,
  isInSeeds = false,
  seedSetFull = false,
}: PosterTileProps) {
  const [posterHidden, setPosterHidden] = useState(false)
  const showPoster = Boolean(item.poster_url) && !posterHidden
  const label = formatTitle(item.title)
  const isStrip = variant === "strip"
  const frameVariant = isStrip ? "strip" : "hero"
  const canAddSeed = Boolean(onAddSeed) && !isInSeeds
  const frameClass = [
    "poster-tile",
    isStrip ? "poster-tile--strip" : "",
    showPoster ? "has-poster" : "",
    isInSeeds ? "is-in-seeds" : "",
    seedSetFull ? "is-at-limit" : "",
  ]
    .filter(Boolean)
    .join(" ")
  const onPosterError = () => setPosterHidden(true)

  const frame = (
    <PosterFrame
      variant={frameVariant}
      className={frameClass}
      interactive={canAddSeed}
      disabled={addSeedDisabled || seedSetFull}
      title={seedSetFull ? "Seed set full (max 5)" : undefined}
      ariaLabel={
        canAddSeed
          ? `Add ${label} to starting movies`
          : isInSeeds
            ? `${label} is in your starting movies`
            : undefined
      }
      onClick={canAddSeed ? onAddSeed : undefined}
    >
      <PosterArt
        showPoster={showPoster}
        posterUrl={item.poster_url}
        onPosterError={onPosterError}
      />
      {rank != null && <span className="poster-rank">{`#${rank}`}</span>}
    </PosterFrame>
  )

  if (isStrip) {
    if (frameOnly) {
      return <div className="poster-shelf-item poster-shelf-item--frame-only">{frame}</div>
    }
    return (
      <div className="poster-shelf-item">
        {frame}
        <p className="poster-shelf-caption">{label}</p>
      </div>
    )
  }

  return (
    <div className="poster-shelf-item poster-shelf-item--default">
      {frame}
      <h3 className="poster-shelf-caption poster-shelf-caption--title">{label}</h3>
    </div>
  )
}
