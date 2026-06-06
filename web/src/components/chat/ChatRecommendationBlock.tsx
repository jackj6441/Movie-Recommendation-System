import type { RecommendationResponse } from "../../types"
import { HeroPick } from "../results/HeroPick"
import { MoreMoviesStrip } from "./MoreMoviesStrip"

type ChatRecommendationBlockProps = {
  data: RecommendationResponse
  onMoreLike?: (movieId: number, title: string) => void
  moreLikeDisabled?: boolean
}

export function ChatRecommendationBlock({
  data,
  onMoreLike,
  moreLikeDisabled = false,
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

  return (
    <div className="chat-rec-block">
      <HeroPick
        item={hero}
        actions={
          onMoreLike ? (
            <button
              type="button"
              className="hero-secondary-action"
              disabled={moreLikeDisabled}
              onClick={() => onMoreLike(hero.movie_id, hero.title)}
            >
              More like this
            </button>
          ) : undefined
        }
      />
      {rest.length > 0 && <MoreMoviesStrip items={rest} />}
    </div>
  )
}
