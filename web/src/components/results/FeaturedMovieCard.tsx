import { useState } from "react"
import type { RecommendationItem, RagExplanationItem } from "../../types"
import { formatTitle } from "../../utils/format"

const FEATURED_CARD_OVERLAY =
  "linear-gradient(180deg, rgba(20, 18, 16, 0.08), rgba(20, 18, 16, 0.88))"

type FeaturedMovieCardProps = {
  recommendation: RecommendationItem
  ragItem?: RagExplanationItem
  index: number
}

export function FeaturedMovieCard({ recommendation, ragItem, index }: FeaturedMovieCardProps) {
  const [posterHidden, setPosterHidden] = useState(false)
  const showPoster = Boolean(recommendation.poster_url) && !posterHidden

  return (
    <article
      className={`movie-card${showPoster ? " has-poster" : ""}`}
      style={
        showPoster
          ? {
              backgroundImage: `${FEATURED_CARD_OVERLAY}, url(${recommendation.poster_url})`,
              backgroundSize: "cover",
              backgroundPosition: "center",
            }
          : undefined
      }
    >
      {recommendation.poster_url && (
        <img
          className="movie-card-poster-probe"
          src={recommendation.poster_url}
          alt=""
          onError={() => setPosterHidden(true)}
        />
      )}
      <span className="movie-rank">#{index + 1}</span>
      <h3>{formatTitle(recommendation.title)}</h3>
      {ragItem && <p className="movie-reason">{ragItem.reason}</p>}
    </article>
  )
}
