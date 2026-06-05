import type { ChatTurn } from "../../types"
import { ChatRecommendationBlock } from "./ChatRecommendationBlock"

type ChatThreadProps = {
  turns: ChatTurn[]
  onNewChat: () => void
}

export function ChatThread({ turns, onNewChat }: ChatThreadProps) {
  return (
    <div className="chat-thread" role="log" aria-live="polite" aria-relevant="additions text">
      {turns.map((turn) => (
        <article
          key={turn.id}
          className={`chat-bubble chat-bubble--${turn.role}${turn.streaming ? " is-streaming" : ""}`}
        >
          <span className="chat-bubble-label">{turn.role === "user" ? "You" : "Assistant"}</span>
          <p className="chat-bubble-text">{turn.content || (turn.streaming ? "…" : "")}</p>
          {turn.role === "assistant" && turn.final?.recommendations && (
            <ChatRecommendationBlock data={turn.final.recommendations} onNewChat={onNewChat} />
          )}
        </article>
      ))}
    </div>
  )
}
