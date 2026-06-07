import type { RecommendationItem } from "../../types"
import { seedAddState } from "../../lib/seedAdd"
import { formatTitle } from "../../utils/format"
import { PosterTile } from "../results/PosterTile"

type MoreMoviesStripProps = {
  items: RecommendationItem[]
  seedMovieIds?: number[]
  onAddSeed?: (movieId: number, title: string) => void
  addSeedDisabled?: boolean
}

export function MoreMoviesStrip({
  items,
  seedMovieIds = [],
  onAddSeed,
  addSeedDisabled = false,
}: MoreMoviesStripProps) {
  const scrollable = items.length > 4

  return (
    <section className="more-movies-section" aria-label="More movies you might like">
      <h3 className="subsection-title more-movies-section-title">More movies you might like</h3>
      <div className="more-movies-strip-stage">
        <div
          className={`more-movies-strip-scroller${scrollable ? " is-scrollable" : ""}`}
          tabIndex={scrollable ? 0 : undefined}
          aria-label={scrollable ? "Scroll for more movie picks" : undefined}
        >
          <div className="more-movies-strip-track">
            <div
              className="more-movies-strip-row more-movies-strip-row--frames"
              role="list"
            >
              {items.map((item) => {
                const addState = seedAddState(item.movie_id, seedMovieIds)
                const rank = items.indexOf(item) + 2
                return (
                  <div key={item.movie_id} role="listitem" className="more-movies-strip-cell">
                    <PosterTile
                      item={item}
                      rank={rank}
                      variant="strip"
                      frameOnly
                      isInSeeds={addState.isInSeeds}
                      seedSetFull={addState.seedSetFull}
                      addSeedDisabled={addSeedDisabled}
                      onAddSeed={
                        onAddSeed && !addState.isInSeeds
                          ? () => onAddSeed(item.movie_id, item.title)
                          : undefined
                      }
                    />
                  </div>
                )
              })}
            </div>
            <div className="more-movies-strip-row more-movies-strip-row--captions">
              {items.map((item) => (
                <p key={item.movie_id} className="more-movies-strip-caption">
                  {formatTitle(item.title)}
                </p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
