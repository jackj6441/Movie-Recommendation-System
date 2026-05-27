// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest"
import { cleanup, render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import App from "./App"

const jsonResponse = (payload: unknown) =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve(payload),
  } as Response)

describe("App RAG explanations", () => {
  let recommendationItems: { movie_id: number; title: string; score: number }[]
  let ragItems: { movie_id: number; reason: string; evidence: string[] }[]
  let recommendationsOk: boolean
  let ragOk: boolean

  beforeEach(() => {
    recommendationsOk = true
    ragOk = true
    recommendationItems = [{ movie_id: 239, title: "Some Movie", score: 0.9 }]
    ragItems = [
      {
        movie_id: 239,
        reason: "It keeps the same light adventure pattern.",
        evidence: ["seed_set", "content_signal"],
      },
    ]

    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = input.toString()

        if (url.endsWith("/genres")) {
          return jsonResponse([{ name: "Comedy" }, { name: "Drama" }])
        }

        if (url.includes("/genres/all/seeds")) {
          return jsonResponse({ seeds: [{ movie_id: 1, title: "Toy Story (1995)" }] })
        }

        if (url.endsWith("/recommendations")) {
          if (!recommendationsOk) {
            return Promise.resolve({
              ok: false,
              status: 500,
              json: () => Promise.resolve({ detail: "boom" }),
            } as Response)
          }

          return jsonResponse({
            items: recommendationItems,
            seed_movies: [{ movie_id: 1, title: "Toy Story (1995)" }],
            anchor_source: "seed_set",
            model_version: "test-model",
          })
        }

        if (url.endsWith("/rag/explanations")) {
          if (!ragOk) {
            return Promise.reject(new Error("RAG unavailable"))
          }

          return jsonResponse({
            summary: "These picks match your seed set through shared tone and genre signals.",
            items: ragItems,
            explanation_source: "rag",
          })
        }

        if (url.endsWith("/explanations")) {
          return jsonResponse({
            user_id: null,
            model_version: "test-model",
            alpha: 0.5,
            anchor_movie: { movie_id: 1, title: "Toy Story (1995)" },
            topk: [{ movie_id: 239, title: "Some Movie", ncf: 0.4, content: 0.5, final: 0.9 }],
            similar_movies: [],
            content_available: true,
          })
        }

        throw new Error(`Unhandled request: ${url}`)
      })
    )
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it("requests and displays the RAG explanation after recommendations are generated", async () => {
    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    expect(await screen.findByText("These picks match your seed set through shared tone and genre signals.")).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith(
      "http://reco-api:8000/rag/explanations",
      expect.objectContaining({ method: "POST" })
    )
  })

  it("displays RAG item explanations in recommendation order", async () => {
    recommendationItems = [
      { movie_id: 101, title: "First Recommendation", score: 0.9 },
      { movie_id: 102, title: "Second Recommendation", score: 0.8 },
      { movie_id: 103, title: "Third Recommendation", score: 0.7 },
    ]
    ragItems = [
      { movie_id: 103, reason: "Third reason", evidence: ["content_signal"] },
      { movie_id: 101, reason: "First reason", evidence: ["seed_set"] },
      { movie_id: 102, reason: "Second reason", evidence: ["hybrid_score"] },
    ]

    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    const aiExplanation = screen.getByRole("heading", { name: "AI Explanation" }).closest(".card")
    expect(aiExplanation).not.toBeNull()

    const first = within(aiExplanation as HTMLElement).getByText("First Recommendation")
    const second = within(aiExplanation as HTMLElement).getByText("Second Recommendation")
    const third = within(aiExplanation as HTMLElement).getByText("Third Recommendation")

    expect(first.compareDocumentPosition(second)).toBe(Node.DOCUMENT_POSITION_FOLLOWING)
    expect(second.compareDocumentPosition(third)).toBe(Node.DOCUMENT_POSITION_FOLLOWING)
  })

  it("does not request RAG explanations when recommendation generation fails", async () => {
    recommendationsOk = false

    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    expect(await screen.findByText("Error: Request failed: 500")).toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalledWith(
      "http://reco-api:8000/rag/explanations",
      expect.anything()
    )
  })

  it("keeps recommendations usable when the RAG explanation request fails", async () => {
    ragOk = false

    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    expect(await screen.findByText("Some Movie")).toBeInTheDocument()
    expect(screen.getByText("AI explanation unavailable. Showing recommendations normally.")).toBeInTheDocument()
    expect(screen.getByText("AI explanation will appear here when available.")).toBeInTheDocument()
  })
})

async function requestRecommendations(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "跳过" }))
  await user.click(await screen.findByRole("button", { name: "选择" }))
  await user.click(screen.getByRole("button", { name: "Recommend" }))
}
