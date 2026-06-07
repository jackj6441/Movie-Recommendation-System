import { useState } from "react"
import type { RecommendationItem } from "../../types"
import { formatTitle } from "../../utils/format"

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
        className="hero-pick__poster"
        src={posterUrl}
        alt=""
        onError={onPosterError}
      />
    )
  }
  return <div className="hero-pick__fallback" aria-hidden="true" />
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

  const frame = onAddSeed && !isInSeeds ? (
    <button
      type="button"
      className={`hero-pick__frame hero-pick--interactive${
        seedSetFull ? " is-at-limit" : ""
      }`}
      disabled={addSeedDisabled || seedSetFull}
      title={seedSetFull ? "Seed set full (max 5)" : undefined}
      aria-label={`Add ${label} to starting movies`}
      onClick={onAddSeed}
    >
      <HeroPoster
        showPoster={showPoster}
        posterUrl={item.poster_url}
        onPosterError={onPosterError}
      />
    </button>
  ) : (
    <div className="hero-pick__frame">
      <HeroPoster
        showPoster={showPoster}
        posterUrl={item.poster_url}
        onPosterError={onPosterError}
      />
    </div>
  )

  return (
    <article
      className={shelfClass}
      aria-label={isInSeeds ? `${label} is in your starting movies` : undefined}
    >
      {frame}
      <HeroCaption label={label} isInSeeds={isInSeeds} />
    </article>
  )
}
