import type { RecommendationResponse } from "../../types"
import { HeroPick } from "../results/HeroPick"
import { PosterTile } from "../results/PosterTile"

type ChatRecommendationBlockProps = {
  data: RecommendationResponse
  onNewChat: () => void
  onMoreLike?: (movieId: number, title: string) => void
  moreLikeDisabled?: boolean
}

export function ChatRecommendationBlock({
  data,
  onNewChat,
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
          <>
            {onMoreLike && (
              <button
                type="button"
                className="hero-secondary-action"
                disabled={moreLikeDisabled}
                onClick={() => onMoreLike(hero.movie_id, hero.title)}
              >
                More like this
              </button>
            )}
            <button type="button" className="hero-secondary-action" onClick={onNewChat}>
              Start over
            </button>
          </>
        }
      />
      {rest.length > 0 && (
        <>
          <h3 className="subsection-title">More movies you might like</h3>
          <div className="more-movies-grid">
            {rest.map((item, index) => (
              <PosterTile
                key={item.movie_id}
                item={item}
                rank={index < 2 ? index + 2 : undefined}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
