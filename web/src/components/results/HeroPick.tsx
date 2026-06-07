import { useState } from "react"
import type { RecommendationItem } from "../../types"
import { formatTitle } from "../../utils/format"

const HERO_SCRIM = [
  "linear-gradient(90deg, rgba(19, 27, 24, 0.92) 0%, rgba(19, 27, 24, 0.72) 39%, rgba(19, 27, 24, 0.2) 70%, rgba(19, 27, 24, 0.08) 100%)",
  "linear-gradient(180deg, rgba(19, 27, 24, 0.08), rgba(19, 27, 24, 0.42))",
].join(", ")

type HeroPickProps = {
  item: RecommendationItem
  onAddSeed?: () => void
  addSeedDisabled?: boolean
  isInSeeds?: boolean
  seedSetFull?: boolean
}

function heroBody(item: RecommendationItem) {
  return (
    <>
      <span className="hero-rank">#1</span>
      <span className="hero-kicker">Tonight&apos;s strongest match</span>
      <h2 className="hero-title">{formatTitle(item.title)}</h2>
    </>
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
  const posterStyle = showPoster
    ? { backgroundImage: `${HERO_SCRIM}, url(${item.poster_url})` }
    : undefined
  const posterProbe = item.poster_url ? (
    <img
      className="hero-pick-probe"
      src={item.poster_url}
      alt=""
      onError={() => setPosterHidden(true)}
    />
  ) : null

  if (isInSeeds) {
    return (
      <article
        className={`hero-pick is-in-seeds${showPoster ? " has-poster" : ""}`}
        style={posterStyle}
        aria-label={`${label} is in your starting movies`}
      >
        {posterProbe}
        <div className="hero-pick-body">{heroBody(item)}</div>
      </article>
    )
  }

  if (onAddSeed) {
    const atLimit = seedSetFull
    return (
      <button
        type="button"
        className={`hero-pick hero-pick--interactive${atLimit ? " is-at-limit" : ""}${
          showPoster ? " has-poster" : ""
        }`}
        style={posterStyle}
        disabled={addSeedDisabled || atLimit}
        title={atLimit ? "Seed set full (max 5)" : undefined}
        aria-label={`Add ${label} to starting movies`}
        onClick={onAddSeed}
      >
        {posterProbe}
        <div className="hero-pick-body">{heroBody(item)}</div>
      </button>
    )
  }

  return (
    <article
      className={`hero-pick${showPoster ? " has-poster" : ""}`}
      style={posterStyle}
    >
      {posterProbe}
      <div className="hero-pick-body">{heroBody(item)}</div>
    </article>
  )
}
