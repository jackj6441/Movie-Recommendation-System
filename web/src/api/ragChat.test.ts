import { afterEach, describe, expect, it, vi } from "vitest"
import { postRagChat } from "./ragChat"

describe("postRagChat", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("handles final-only SSE without token events", async () => {
    const final = {
      session_id: "sess-1",
      turn_id: "turn-1",
      needs_clarification: true,
      needs_disambiguation: true,
      clarification_reason: "no_resolvable_seeds",
      disambiguation_candidates: [
        { movie_id: 50, title: "Candidate Movie (2000)", year: 2000, genres: ["Drama"] },
      ],
      context: { seeds: [], genres: [], year_min: null, year_max: null },
      recommendations: null,
      assistant_message: "Pick a starting movie from the list below.",
      explanation_source: "rag",
      model_version: "test",
    }
    const body = `event: final\ndata: ${JSON.stringify(final)}\n\n`

    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          text: () => Promise.resolve(body),
        } as Response)
      )
    )

    const result = await postRagChat({
      session_id: null,
      message: "zzzznotamovie",
      genres: [],
    })

    expect(result.tokens).toBe("")
    expect(result.assistantMessage).toBe("Pick a starting movie from the list below.")
    expect(result.final.needs_disambiguation).toBe(true)
  })
})
