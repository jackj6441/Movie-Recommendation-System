import type { ChatTurn } from "../../types"
import { ChatDebugPanel } from "./ChatDebugPanel"
import { ChatRecommendationBlock } from "./ChatRecommendationBlock"
import { DisambiguationPicker } from "./DisambiguationPicker"

type ChatThreadProps = {
  turns: ChatTurn[]
  seedMovieIds?: number[]
  onAddSeed?: (movieId: number, title: string) => void
  onDisambiguationSubmit?: (movieIds: number[]) => void
  onDisambiguationGenrePick?: (genre: string) => void
  pickerDisabled?: boolean
  addSeedDisabled?: boolean
}

export function ChatThread({
  turns,
  seedMovieIds = [],
  onAddSeed,
  onDisambiguationSubmit,
  onDisambiguationGenrePick,
  pickerDisabled = false,
  addSeedDisabled = false,
}: ChatThreadProps) {
  return (
    <div className="chat-thread" role="log" aria-live="polite" aria-relevant="additions text">
      {turns.map((turn) => {
        const isUser = turn.role === "user"

        return (
          <article
            key={turn.id}
            data-turn-id={turn.id}
            className={`chat-turn chat-bubble chat-bubble--${turn.role}${
              turn.streaming ? " is-streaming" : ""
            }`}
          >
            <span className="chat-turn-label">{isUser ? "You" : "Assistant"}</span>
            {turn.content || turn.streaming ? (
              <p className="chat-turn-text chat-bubble-text">
                {turn.content || (turn.streaming ? "…" : "")}
              </p>
            ) : null}
            {turn.role === "assistant" &&
              turn.view?.outcome === "disambiguate" &&
              turn.view.disambiguation &&
              onDisambiguationSubmit && (
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
                seedMovieIds={seedMovieIds}
                onAddSeed={onAddSeed}
                addSeedDisabled={addSeedDisabled}
              />
            )}
            {turn.role === "assistant" && turn.view?.debug && (
              <ChatDebugPanel debug={turn.view.debug} />
            )}
          </article>
        )
      })}
    </div>
  )
}
