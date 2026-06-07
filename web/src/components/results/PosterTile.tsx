import { useState } from "react"
import type { RecommendationItem } from "../../types"
import { formatTitle } from "../../utils/format"

type PosterTileProps = {
  item: RecommendationItem
  rank?: number
  variant?: "default" | "strip"
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
        className="poster-tile__poster"
        src={posterUrl}
        alt=""
        loading="lazy"
        decoding="async"
        onError={onPosterError}
      />
    )
  }
  return <div className="poster-tile__fallback" aria-hidden="true" />
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
  const isStrip = variant === "strip"
  const frameClass = `poster-tile${isStrip ? " poster-tile--strip" : ""}${
    showPoster ? " has-poster" : ""
  }${isInSeeds ? " is-in-seeds" : ""}${onAddSeed && seedSetFull ? " is-at-limit" : ""}${
    onAddSeed ? " poster-tile--interactive" : ""
  }`
  const onPosterError = () => setPosterHidden(true)

  const frameBody = (
    <>
      <PosterArt
        showPoster={showPoster}
        posterUrl={item.poster_url}
        onPosterError={onPosterError}
      />
      {rank != null && <span className="poster-rank">{`#${rank}`}</span>}
    </>
  )

  const frame =
    onAddSeed && !isInSeeds ? (
      <button
        type="button"
        className={frameClass}
        disabled={addSeedDisabled || seedSetFull}
        title={seedSetFull ? "Seed set full (max 5)" : undefined}
        aria-label={`Add ${label} to starting movies`}
        onClick={onAddSeed}
      >
        {frameBody}
      </button>
    ) : (
      <div className={frameClass} aria-label={isInSeeds ? `${label} is in your starting movies` : undefined}>
        {frameBody}
      </div>
    )

  if (isStrip) {
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
