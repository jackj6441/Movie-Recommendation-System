import type { ChatTurn } from "../../types"
import { ChatDebugPanel } from "./ChatDebugPanel"
import { ChatRecommendationBlock } from "./ChatRecommendationBlock"
import { DisambiguationPicker } from "./DisambiguationPicker"

type ChatThreadProps = {
  turns: ChatTurn[]
  onMoreLike?: (movieId: number, title: string) => void
  onDisambiguationSubmit?: (movieIds: number[]) => void
  onDisambiguationGenrePick?: (genre: string) => void
  pickerDisabled?: boolean
  moreLikeDisabled?: boolean
}

export function ChatThread({
  turns,
  onNewChat,
  onMoreLike,
  onDisambiguationSubmit,
  onDisambiguationGenrePick,
  pickerDisabled = false,
  moreLikeDisabled = false,
}: ChatThreadProps) {
  return (
    <div className="chat-thread" role="log" aria-live="polite" aria-relevant="additions text">
      {turns.map((turn) => (
        <article
          key={turn.id}
          data-turn-id={turn.id}
          className={`chat-bubble chat-bubble--${turn.role}${turn.streaming ? " is-streaming" : ""}`}
        >
          <span className="chat-bubble-label">{turn.role === "user" ? "You" : "Assistant"}</span>
          <p className="chat-bubble-text">{turn.content || (turn.streaming ? "…" : "")}</p>
          {turn.role === "assistant" && turn.view?.outcome === "disambiguate" && turn.view.disambiguation && onDisambiguationSubmit && (
            <DisambiguationPicker
              candidates={turn.view.disambiguation.candidates}
              genreOptions={turn.view.disambiguation.genreOptions}
              disabled={pickerDisabled}
              onSubmit={onDisambiguationSubmit}
              onGenrePick={onDisambiguationGenrePick}
            />
          )}
          {turn.role === "assistant" && turn.view?.recommendations && (
            <ChatRecommendationBlock
              data={turn.view.recommendations}
              onMoreLike={onMoreLike}
              moreLikeDisabled={moreLikeDisabled}
            />
          )}
          {turn.role === "assistant" && turn.view?.debug && (
            <ChatDebugPanel debug={turn.view.debug} />
          )}
        </article>
      ))}
    </div>
  )
}
