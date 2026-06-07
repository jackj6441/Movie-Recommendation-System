type HeroDetailsProps = {
  label: string
  genres?: string[]
  overview?: string
  watchUrl?: string
  isInSeeds?: boolean
}

function ExternalLinkIcon() {
  return (
    <svg
      className="hero-details__watch-icon"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <polyline points="15 3 21 3 21 9" />
      <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
  )
}

export function HeroDetails({
  label,
  genres = [],
  overview,
  watchUrl,
  isInSeeds = false,
}: HeroDetailsProps) {
  const hasOverview = Boolean(overview?.trim())
  const hasGenres = genres.length > 0

  return (
    <div className="hero-details">
      <span className="hero-details__label">#1 · Top pick</span>
      <h2 className="hero-details__title">{label}</h2>
      {isInSeeds && (
        <span className="hero-details__status">In your starting movies</span>
      )}
      {hasOverview && <p className="hero-details__overview">{overview}</p>}
      {hasGenres && (
        <ul className="hero-details__genres" aria-label="Genres">
          {genres.map((genre) => (
            <li key={genre}>
              <span className="hero-details__genre-pill">{genre}</span>
            </li>
          ))}
        </ul>
      )}
      {watchUrl && (
        <a
          className="hero-details__watch"
          href={watchUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          Where to watch
          <ExternalLinkIcon />
        </a>
      )}
    </div>
  )
}
