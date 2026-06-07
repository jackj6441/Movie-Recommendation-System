import { useState } from "react"
import { MAX_SEEDS } from "../../config"
import { PosterFrame } from "../results/PosterFrame"
import type { DisambiguationCandidate } from "../../types"
import { formatTitle } from "../../utils/format"

type DisambiguationPickerProps = {
  candidates: DisambiguationCandidate[]
  genreOptions?: string[]
  disabled?: boolean
  onSubmit: (movieIds: number[]) => void
  onGenrePick?: (genre: string) => void
}

function DisambiguationFrame({
  candidate,
  isSelected,
  disabled,
  atLimit,
  onToggle,
}: {
  candidate: DisambiguationCandidate
  isSelected: boolean
  disabled: boolean
  atLimit: boolean
  onToggle: () => void
}) {
  const [posterHidden, setPosterHidden] = useState(false)
  const posterUrl = candidate.poster_thumb_url ?? candidate.poster_url
  const showPoster = Boolean(posterUrl) && !posterHidden
  const label = formatTitle(candidate.title)
  const yearSuffix = candidate.year != null ? ` (${candidate.year})` : ""
  const genreLine = candidate.genres?.length ? candidate.genres.join(", ") : null

  return (
    <div className="disambiguation-shelf-item">
      <PosterFrame
        variant="strip"
        className={`disambiguation-frame${isSelected ? " is-selected" : ""}${
          showPoster ? " has-poster" : ""
        }`}
        interactive
        ariaPressed={isSelected}
        ariaLabel={`${label}${yearSuffix}`}
        disabled={disabled || atLimit}
        onClick={onToggle}
      >
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
      <p className="disambiguation-shelf-caption">
        <span className="disambiguation-shelf-title">
          {label}
          {yearSuffix}
        </span>
        {genreLine && <span className="disambiguation-shelf-genres">{genreLine}</span>}
      </p>
    </div>
  )
}

export function DisambiguationPicker({
  candidates,
  genreOptions = [],
  disabled = false,
  onSubmit,
  onGenrePick,
}: DisambiguationPickerProps) {
  const [selected, setSelected] = useState<number[]>([])
  const hasGenreOptions = genreOptions.length > 0 && onGenrePick != null

  const toggle = (movieId: number) => {
    if (disabled) return
    setSelected((prev) => {
      if (prev.includes(movieId)) {
        return prev.filter((id) => id !== movieId)
      }
      if (prev.length >= MAX_SEEDS) {
        return prev
      }
      return [...prev, movieId]
    })
  }

  return (
    <div className="disambiguation-picker" role="group" aria-label="Pick seed movies or genre">
      {hasGenreOptions && (
        <div className="disambiguation-genre-row" role="group" aria-label="Genre options">
          {genreOptions.map((genre) => (
            <button
              key={genre}
              type="button"
              className="disambiguation-genre-pill"
              disabled={disabled || selected.length > 0}
              onClick={() => onGenrePick(genre)}
            >
              {genre}
            </button>
          ))}
        </div>
      )}
      <div className="disambiguation-picker-grid">
        {candidates.map((candidate) => {
          const isSelected = selected.includes(candidate.movie_id)
          const atLimit = !isSelected && selected.length >= MAX_SEEDS

          return (
            <DisambiguationFrame
              key={candidate.movie_id}
              candidate={candidate}
              isSelected={isSelected}
              disabled={disabled}
              atLimit={atLimit}
              onToggle={() => toggle(candidate.movie_id)}
            />
          )
        })}
      </div>
      <button
        type="button"
        className="chat-send-btn disambiguation-submit"
        disabled={disabled || selected.length === 0}
        onClick={() => onSubmit(selected)}
      >
        Use as Seed Set
      </button>
    </div>
  )
}
