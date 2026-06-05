import type { ChatTurn } from "../../types"
import { ChatRecommendationBlock } from "./ChatRecommendationBlock"
import { DisambiguationPicker } from "./DisambiguationPicker"

type ChatThreadProps = {
  turns: ChatTurn[]
  onNewChat: () => void
  onMoreLike?: (movieId: number, title: string) => void
  onDisambiguationSubmit?: (movieIds: number[]) => void
  pickerDisabled?: boolean
  moreLikeDisabled?: boolean
}

export function ChatThread({
  turns,
  onNewChat,
  onMoreLike,
  onDisambiguationSubmit,
  pickerDisabled = false,
  moreLikeDisabled = false,
}: ChatThreadProps) {
  return (
    <div className="chat-thread" role="log" aria-live="polite" aria-relevant="additions text">
      {turns.map((turn) => (
        <article
          key={turn.id}
          className={`chat-bubble chat-bubble--${turn.role}${turn.streaming ? " is-streaming" : ""}`}
        >
          <span className="chat-bubble-label">{turn.role === "user" ? "You" : "Assistant"}</span>
          <p className="chat-bubble-text">{turn.content || (turn.streaming ? "…" : "")}</p>
          {turn.role === "assistant" && turn.final?.needs_disambiguation && turn.final.disambiguation_candidates && onDisambiguationSubmit && (
            <DisambiguationPicker
              candidates={turn.final.disambiguation_candidates}
              disabled={pickerDisabled}
              onSubmit={onDisambiguationSubmit}
            />
          )}
          {turn.role === "assistant" && turn.final?.recommendations && (
            <ChatRecommendationBlock
              data={turn.final.recommendations}
              onNewChat={onNewChat}
              onMoreLike={onMoreLike}
              moreLikeDisabled={moreLikeDisabled}
            />
          )}
        </article>
      ))}
    </div>
  )
}
