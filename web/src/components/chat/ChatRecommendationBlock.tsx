import { seedAddState } from "../../lib/seedAdd"
import type { RecommendationResponse } from "../../types"
import { HeroPick } from "../results/HeroPick"
import { MoreMoviesStrip } from "./MoreMoviesStrip"

type ChatRecommendationBlockProps = {
  data: RecommendationResponse
  seedMovieIds?: number[]
  onAddSeed?: (movieId: number, title: string) => void
  addSeedDisabled?: boolean
}

export function ChatRecommendationBlock({
  data,
  seedMovieIds = [],
  onAddSeed,
  addSeedDisabled = false,
}: ChatRecommendationBlockProps) {
  const items = data.items
  if (items.length === 0) {
    return (
      <div className="chat-rec-empty" role="status">
        <p>No movies matched that request. Try another genre or mention a favorite title.</p>
      </div>
    )
  }

  const hero = items[0]
  const rest = items.slice(1)
  const heroAddState = seedAddState(hero.movie_id, seedMovieIds)

  return (
    <section className="chat-rec-block" aria-label="Recommendations">
      <HeroPick
        item={hero}
        isInSeeds={heroAddState.isInSeeds}
        seedSetFull={heroAddState.seedSetFull}
        addSeedDisabled={addSeedDisabled}
        onAddSeed={
          onAddSeed && !heroAddState.isInSeeds
            ? () => onAddSeed(hero.movie_id, hero.title)
            : undefined
        }
      />
      {rest.length > 0 && (
        <MoreMoviesStrip
          items={rest}
          seedMovieIds={seedMovieIds}
          onAddSeed={onAddSeed}
          addSeedDisabled={addSeedDisabled}
        />
      )}
    </section>
  )
}
