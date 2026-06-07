import { describe, expect, it } from "vitest"
import { normalizeChatTurn, parseRagChatFinal, toChatTurnView } from "./chatTurnView"
import type { RagChatFinal } from "../types"

const readyFinal: RagChatFinal = {
  session_id: "sess-1",
  turn_id: "turn-1",
  needs_clarification: false,
  needs_disambiguation: false,
  context: { seeds: [], genres: ["Comedy"], year_min: null, year_max: null },
  recommendations: {
    items: [{ movie_id: 1, title: "Toy Story (1995)", score: 0.9 }],
    seed_movies: [{ movie_id: 1, title: "Toy Story (1995)" }],
    anchor_source: "seed",
    model_version: "test",
  },
  assistant_message: "Here are your picks.",
  explanation_source: "rag",
}

describe("parseRagChatFinal", () => {
  it("rejects non-object payloads", () => {
    expect(() => parseRagChatFinal(null)).toThrow(/object/)
  })

  it("requires core final fields", () => {
    expect(() => parseRagChatFinal({ session_id: "s" })).toThrow(/turn_id/)
  })

  it("parses a ready final payload", () => {
    const parsed = parseRagChatFinal(readyFinal)
    expect(parsed.session_id).toBe("sess-1")
    expect(parsed.context.genres).toEqual(["Comedy"])
  })
})

describe("toChatTurnView", () => {
  it("maps ready turns with recommendations", () => {
    const view = toChatTurnView(readyFinal)
    expect(view.outcome).toBe("ready")
    expect(view.recommendations?.items).toHaveLength(1)
    expect(view.disambiguation).toBeNull()
    expect(view.assistantMessage).toBe("Here are your picks.")
  })

  it("prefers streamed text when assistant_message is empty", () => {
    const view = toChatTurnView(
      { ...readyFinal, assistant_message: "" },
      { streamedText: "Streamed copy." },
    )
    expect(view.assistantMessage).toBe("Streamed copy.")
  })

  it("maps disambiguation turns", () => {
    const view = toChatTurnView({
      ...readyFinal,
      needs_clarification: true,
      needs_disambiguation: true,
      clarification_reason: "no_resolvable_seeds",
      recommendations: null,
      disambiguation_candidates: [{ movie_id: 50, title: "Candidate (2000)" }],
      disambiguation_genre_options: ["Drama"],
      assistant_message: "Pick a movie.",
    })
    expect(view.outcome).toBe("disambiguate")
    expect(view.disambiguation?.candidates).toHaveLength(1)
    expect(view.disambiguation?.genreOptions).toEqual(["Drama"])
  })

  it("maps clarify and error outcomes", () => {
    const clarify = toChatTurnView({
      ...readyFinal,
      needs_clarification: true,
      clarification_reason: "missing_genre_and_title",
      recommendations: null,
      assistant_message: "Pick genres.",
    })
    expect(clarify.outcome).toBe("clarify")

    const error = toChatTurnView({
      ...readyFinal,
      rank_error: "content_unavailable",
      recommendations: null,
      assistant_message: "Unavailable.",
    })
    expect(error.outcome).toBe("error")
    expect(error.rankError).toBe("content_unavailable")
  })
})

describe("normalizeChatTurn", () => {
  it("upgrades legacy final payloads on assistant turns", () => {
    const normalized = normalizeChatTurn({
      id: "a1",
      role: "assistant",
      content: "Here are your picks.",
      final: readyFinal,
    })
    expect(normalized.view?.outcome).toBe("ready")
    expect(normalized.view?.sessionId).toBe("sess-1")
  })

  it("leaves user turns unchanged", () => {
    const turn = { id: "u1", role: "user" as const, content: "hello" }
    expect(normalizeChatTurn(turn)).toBe(turn)
  })
})
