import { useState } from "react"
import type { RecommendationItem } from "../../types"
import { formatTitle } from "../../utils/format"
import { PosterFrame } from "./PosterFrame"

type HeroPickProps = {
  item: RecommendationItem
  onAddSeed?: () => void
  addSeedDisabled?: boolean
  isInSeeds?: boolean
  seedSetFull?: boolean
}

function HeroPoster({
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
        onError={onPosterError}
      />
    )
  }
  return <div className="poster-frame__fallback" aria-hidden="true" />
}

function HeroCaption({
  label,
  isInSeeds,
}: {
  label: string
  isInSeeds: boolean
}) {
  return (
    <div className="hero-pick__caption">
      <span className="hero-pick__label">#1 · Top pick</span>
      <h2 className="hero-pick__title">{label}</h2>
      {isInSeeds && (
        <span className="hero-pick__status">In your starting movies</span>
      )}
    </div>
  )
}

export function HeroPick({
  item,
  onAddSeed,
  addSeedDisabled = false,
  isInSeeds = false,
  seedSetFull = false,
}: HeroPickProps) {
  const [posterHidden, setPosterHidden] = useState(false)
  const showPoster = Boolean(item.poster_url) && !posterHidden
  const label = formatTitle(item.title)
  const shelfClass = `hero-pick${showPoster ? " has-poster" : ""}${
    isInSeeds ? " is-in-seeds" : ""
  }`
  const onPosterError = () => setPosterHidden(true)
  const canAddSeed = Boolean(onAddSeed) && !isInSeeds

  return (
    <article
      className={shelfClass}
      aria-label={isInSeeds ? `${label} is in your starting movies` : undefined}
    >
      <PosterFrame
        variant="hero"
        className={`hero-pick__frame${seedSetFull ? " is-at-limit" : ""}`}
        interactive={canAddSeed}
        disabled={addSeedDisabled || seedSetFull}
        title={seedSetFull ? "Seed set full (max 5)" : undefined}
        ariaLabel={canAddSeed ? `Add ${label} to starting movies` : undefined}
        onClick={canAddSeed ? onAddSeed : undefined}
      >
        <HeroPoster
          showPoster={showPoster}
          posterUrl={item.poster_url}
          onPosterError={onPosterError}
        />
      </PosterFrame>
      <HeroCaption label={label} isInSeeds={isInSeeds} />
    </article>
  )
}
