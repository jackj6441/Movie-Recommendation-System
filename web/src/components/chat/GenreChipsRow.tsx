import { MAX_GENRES } from "../../config"

type GenreChipsRowProps = {
  genres: string[]
  selected: string[]
  loading?: boolean
  disabled?: boolean
  ariaLabel?: string
  onToggle: (genre: string) => void
}

export function GenreChipsRow({
  genres,
  selected,
  loading = false,
  disabled = false,
  ariaLabel = "Genre filters",
  onToggle,
}: GenreChipsRowProps) {
  const visible = genres.slice(0, 12)

  return (
    <div
      className="chat-genre-row"
      role="group"
      aria-label={ariaLabel}
      aria-busy={loading}
    >
      {loading ? (
        <span className="subtle">Loading genres…</span>
      ) : (
        visible.map((genre) => (
          <button
            key={genre}
            type="button"
            className={`chat-genre-chip ${selected.includes(genre) ? "active" : ""}`}
            aria-pressed={selected.includes(genre)}
            disabled={disabled || (!selected.includes(genre) && selected.length >= MAX_GENRES)}
            onClick={() => onToggle(genre)}
          >
            {genre}
          </button>
        ))
      )}
    </div>
  )
}
