import { useState } from "react"
import type { DisambiguationCandidate } from "../../types"
import { formatTitle } from "../../utils/format"

const MAX_PICKS = 5
const POSTER_OVERLAY = "linear-gradient(180deg, rgba(20, 18, 16, 0.05), rgba(20, 18, 16, 0.85))"

type DisambiguationPickerProps = {
  candidates: DisambiguationCandidate[]
  disabled?: boolean
  onSubmit: (movieIds: number[]) => void
}

export function DisambiguationPicker({
  candidates,
  disabled = false,
  onSubmit,
}: DisambiguationPickerProps) {
  const [selected, setSelected] = useState<number[]>([])

  const toggle = (movieId: number) => {
    if (disabled) return
    setSelected((prev) => {
      if (prev.includes(movieId)) {
        return prev.filter((id) => id !== movieId)
      }
      if (prev.length >= MAX_PICKS) {
        return prev
      }
      return [...prev, movieId]
    })
  }

  return (
    <div className="disambiguation-picker" role="group" aria-label="Pick seed movies">
      <p className="disambiguation-picker-lead">
        Which movie did you mean? Select 1–5 movies to start from. These are possible
        matches—not your final recommendations.
      </p>
      <div className="disambiguation-picker-grid">
        {candidates.map((candidate) => {
          const isSelected = selected.includes(candidate.movie_id)
          const posterUrl = candidate.poster_thumb_url ?? candidate.poster_url
          const label = formatTitle(candidate.title)
          const yearSuffix = candidate.year != null ? ` (${candidate.year})` : ""
          const genreLine = candidate.genres?.length ? candidate.genres.join(", ") : null
          const atLimit = !isSelected && selected.length >= MAX_PICKS

          return (
            <button
              key={candidate.movie_id}
              type="button"
              className={`disambiguation-poster-card${isSelected ? " is-selected" : ""}${
                posterUrl ? " has-poster" : ""
              }`}
              aria-pressed={isSelected}
              disabled={disabled || atLimit}
              style={
                posterUrl
                  ? {
                      backgroundImage: `${POSTER_OVERLAY}, url(${posterUrl})`,
                      backgroundSize: "cover",
                      backgroundPosition: "center",
                    }
                  : undefined
              }
              onClick={() => toggle(candidate.movie_id)}
            >
              <span className="disambiguation-poster-title">
                {label}
                {yearSuffix}
              </span>
              {genreLine && (
                <span className="disambiguation-poster-genres">{genreLine}</span>
              )}
            </button>
          )
        })}
      </div>
      <button
        type="button"
        className="chat-send-btn"
        disabled={disabled || selected.length === 0}
        onClick={() => onSubmit(selected)}
      >
        Use as Seed Set
      </button>
    </div>
  )
}
