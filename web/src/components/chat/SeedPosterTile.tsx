import { useState } from "react"
import type { ChatSeedRef } from "../../types"
import { formatTitle } from "../../utils/format"
import { CloseIcon } from "../icons"
import { PosterFrame } from "../results/PosterFrame"

type SeedPosterTileProps = {
  seed: ChatSeedRef
  disabled?: boolean
  onRemove: () => void
}

export function SeedPosterTile({ seed, disabled = false, onRemove }: SeedPosterTileProps) {
  const [posterHidden, setPosterHidden] = useState(false)
  const posterUrl = seed.poster_thumb_url ?? seed.poster_url
  const showPoster = Boolean(posterUrl) && !posterHidden
  const label = formatTitle(seed.title)

  return (
    <div className="taste-seed-tile">
      <button
        type="button"
        className="taste-seed-tile__remove"
        disabled={disabled}
        aria-label={`Remove ${label} from starting movies`}
        onClick={onRemove}
      >
        <PosterFrame variant="strip" className="taste-seed-tile__frame">
          {showPoster && posterUrl ? (
            <img
              className="poster-frame__art"
              src={posterUrl}
              alt=""
              loading="lazy"
              decoding="async"
              onError={() => setPosterHidden(true)}
            />
          ) : (
            <div className="poster-frame__fallback" aria-hidden="true" />
          )}
        </PosterFrame>
        <CloseIcon className="taste-seed-tile__close" size={12} />
      </button>
      <p className="taste-seed-tile__caption" title={label}>
        {label}
      </p>
    </div>
  )
}
