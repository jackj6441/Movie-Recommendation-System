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
    expect(result.view.outcome).toBe("disambiguate")
  })

  it("serializes explicit year bounds in the request body", async () => {
    const body = `event: final\ndata: ${JSON.stringify({
      session_id: "sess-1",
      turn_id: "turn-1",
      needs_clarification: false,
      needs_disambiguation: false,
      context: { seeds: [], genres: ["Comedy"], year_min: 1990, year_max: 2004 },
      recommendations: null,
      assistant_message: "Done.",
      explanation_source: "rag",
      model_version: "test",
    })}\n\n`

    const fetchMock = vi.fn((_input: RequestInfo, init?: RequestInit) => {
      const payload = init?.body ? JSON.parse(String(init.body)) : {}
      expect(payload.year_min).toBe(1990)
      expect(payload.year_max).toBe(2004)
      return Promise.resolve({
        ok: true,
        text: () => Promise.resolve(body),
      } as Response)
    })
    vi.stubGlobal("fetch", fetchMock)

    await postRagChat({
      session_id: "sess-1",
      message: "",
      genres: ["Comedy"],
      year_min: 1990,
      year_max: 2004,
    })
  })

  it("serializes disambiguation_genre in the request body", async () => {
    const body = `event: final\ndata: ${JSON.stringify({
      session_id: "sess-1",
      turn_id: "turn-2",
      needs_clarification: false,
      needs_disambiguation: false,
      context: { seeds: [], genres: ["Drama"], year_min: 2005, year_max: null },
      recommendations: { items: [], seed_movies: [], anchor_source: "seed", model_version: "test" },
      assistant_message: "Drama picks.",
      explanation_source: "rag",
      model_version: "test",
    })}\n\n`

    const fetchMock = vi.fn((_input: RequestInfo, init?: RequestInit) => {
      const payload = init?.body ? JSON.parse(String(init.body)) : {}
      expect(payload.disambiguation_genre).toBe("Drama")
      return Promise.resolve({
        ok: true,
        text: () => Promise.resolve(body),
      } as Response)
    })
    vi.stubGlobal("fetch", fetchMock)

    await postRagChat({
      session_id: "sess-1",
      message: "",
      genres: [],
      disambiguation_genre: "Drama",
    })
  })
})
