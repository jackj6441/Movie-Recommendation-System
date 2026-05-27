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
  let ragExplanationSource: "rag" | "rag_cache" | "deterministic_fallback"
  let recommendationsOk: boolean
  let ragOk: boolean

  beforeEach(() => {
    recommendationsOk = true
    ragOk = true
    ragExplanationSource = "rag"
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
            explanation_source: ragExplanationSource,
            provider: "external",
            provider_model: "should-not-render",
            raw_prompt: "hidden prompt",
            api_key: "sk-test-secret",
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

    const featured = screen.getByRole("heading", { name: "Featured for you" }).closest(".card")
    expect(featured).not.toBeNull()

    const first = within(featured as HTMLElement).getByText("First Recommendation")
    const second = within(featured as HTMLElement).getByText("Second Recommendation")
    const third = within(featured as HTMLElement).getByText("Third Recommendation")

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

  it("shows restrained fallback copy without exposing provider details", async () => {
    ragExplanationSource = "deterministic_fallback"

    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    expect(await screen.findByText("Generated explanation unavailable; showing a safe fallback.")).toBeInTheDocument()
    expect(screen.getByText("These picks match your seed set through shared tone and genre signals.")).toBeInTheDocument()
    expect(screen.queryByText("external")).not.toBeInTheDocument()
    expect(screen.queryByText("should-not-render")).not.toBeInTheDocument()
    expect(screen.queryByText("hidden prompt")).not.toBeInTheDocument()
    expect(screen.queryByText("sk-test-secret")).not.toBeInTheDocument()
  })

  it("shows RAG reasons on top three featured recommendation cards only", async () => {
    recommendationItems = [
      { movie_id: 101, title: "First Recommendation", score: 0.91 },
      { movie_id: 102, title: "Second Recommendation", score: 0.82 },
      { movie_id: 103, title: "Third Recommendation", score: 0.73 },
      { movie_id: 104, title: "Fourth Recommendation", score: 0.64 },
    ]
    ragItems = [
      { movie_id: 101, reason: "First AI reason", evidence: ["seed_set"] },
      { movie_id: 102, reason: "Second AI reason", evidence: ["content_signal"] },
      { movie_id: 103, reason: "Third AI reason", evidence: ["hybrid_score"] },
    ]

    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    const featured = screen.getByRole("heading", { name: "Featured for you" }).closest(".card")
    expect(featured).not.toBeNull()
    expect(within(featured as HTMLElement).getByText("First AI reason")).toBeInTheDocument()
    expect(within(featured as HTMLElement).getByText("Second AI reason")).toBeInTheDocument()
    expect(within(featured as HTMLElement).getByText("Third AI reason")).toBeInTheDocument()

    const moreRecommendations = screen.getByRole("heading", { name: "More recommendations" }).closest(".card")
    expect(moreRecommendations).not.toBeNull()
    expect(within(moreRecommendations as HTMLElement).getByText("Fourth Recommendation")).toBeInTheDocument()
    expect(within(moreRecommendations as HTMLElement).queryByText(/AI reason/)).not.toBeInTheDocument()
  })

  it("keeps the selected seed set visible on the recommendation results page", async () => {
    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    const seedSet = screen.getByRole("heading", { name: "Your seed set" }).closest(".card")
    expect(seedSet).not.toBeNull()
    expect(within(seedSet as HTMLElement).getByText("Toy Story (1995)")).toBeInTheDocument()
  })

  it("keeps the AI explanation panel summary-only after item reasons move into cards", async () => {
    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    const aiExplanation = screen.getByRole("heading", { name: "AI Explanation" }).closest(".card")
    expect(aiExplanation).not.toBeNull()
    expect(within(aiExplanation as HTMLElement).getByText("These picks match your seed set through shared tone and genre signals.")).toBeInTheDocument()
    expect(within(aiExplanation as HTMLElement).queryByText("It keeps the same light adventure pattern.")).not.toBeInTheDocument()
  })

  it("renders featured cards without crashing when fewer than three recommendations exist", async () => {
    recommendationItems = [{ movie_id: 239, title: "Only Movie", score: 0.9 }]
    ragItems = [{ movie_id: 239, reason: "Only reason", evidence: ["seed_set"] }]

    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    const featured = screen.getByRole("heading", { name: "Featured for you" }).closest(".card")
    expect(featured).not.toBeNull()
    expect(within(featured as HTMLElement).getByText("Only Movie")).toBeInTheDocument()
    expect(within(featured as HTMLElement).getByText("Only reason")).toBeInTheDocument()
    expect(within(featured as HTMLElement).queryByText("Top 2")).not.toBeInTheDocument()
    expect(within(featured as HTMLElement).queryByText("Top 3")).not.toBeInTheDocument()
  })

  it("does not expose the api base url in the rendered page", async () => {
    const user = userEvent.setup()
    render(<App />)

    expect(screen.queryByText(/localhost/)).not.toBeInTheDocument()
    expect(screen.queryByText(/reco-api/)).not.toBeInTheDocument()
    expect(screen.queryByText(/apiBase/)).not.toBeInTheDocument()

    await requestRecommendations(user)

    expect(screen.queryByText(/localhost/)).not.toBeInTheDocument()
    expect(screen.queryByText(/reco-api/)).not.toBeInTheDocument()
    expect(screen.queryByText(/apiBase/)).not.toBeInTheDocument()
  })

  it("does not render provider details or secrets even when rag source is rag", async () => {
    ragExplanationSource = "rag"

    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    await screen.findByText("These picks match your seed set through shared tone and genre signals.")
    expect(screen.queryByText("external")).not.toBeInTheDocument()
    expect(screen.queryByText("should-not-render")).not.toBeInTheDocument()
    expect(screen.queryByText("hidden prompt")).not.toBeInTheDocument()
    expect(screen.queryByText("sk-test-secret")).not.toBeInTheDocument()
  })

  it("renders featured card without a reason when RAG items are fewer than recommendations", async () => {
    recommendationItems = [
      { movie_id: 101, title: "First Movie", score: 0.9 },
      { movie_id: 102, title: "Second Movie", score: 0.8 },
      { movie_id: 103, title: "Third Movie", score: 0.7 },
    ]
    ragItems = [
      { movie_id: 101, reason: "First reason", evidence: ["seed_set"] },
      { movie_id: 102, reason: "Second reason", evidence: ["content_signal"] },
    ]

    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    const featured = screen.getByRole("heading", { name: "Featured for you" }).closest(".card")
    expect(featured).not.toBeNull()
    expect(within(featured as HTMLElement).getByText("Third Movie")).toBeInTheDocument()
    expect(within(featured as HTMLElement).queryByText("Third reason")).not.toBeInTheDocument()
    expect(within(featured as HTMLElement).getByText("First reason")).toBeInTheDocument()
    expect(within(featured as HTMLElement).getByText("Second reason")).toBeInTheDocument()
  })

  it("does not render the More recommendations section when all results fit in featured cards", async () => {
    recommendationItems = [
      { movie_id: 101, title: "First Movie", score: 0.9 },
      { movie_id: 102, title: "Second Movie", score: 0.8 },
    ]
    ragItems = [
      { movie_id: 101, reason: "First reason", evidence: ["seed_set"] },
      { movie_id: 102, reason: "Second reason", evidence: ["content_signal"] },
    ]

    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    expect(screen.queryByRole("heading", { name: "More recommendations" })).not.toBeInTheDocument()
  })

  it("disables the Recommend button when no seeds are selected", async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("button", { name: "跳过" }))

    const recommendButton = screen.getByRole("button", { name: "Recommend" })
    expect(recommendButton).toBeDisabled()
  })

  it("shows Loading text on the Recommend button while fetching recommendations", async () => {
    let resolveRecommendations!: (value: Response) => void
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = input.toString()
        if (url.endsWith("/genres")) return jsonResponse([{ name: "Comedy" }])
        if (url.includes("/genres/all/seeds")) return jsonResponse({ seeds: [{ movie_id: 1, title: "Toy Story (1995)" }] })
        if (url.endsWith("/recommendations")) {
          return new Promise<Response>((resolve) => { resolveRecommendations = resolve })
        }
        return jsonResponse({})
      })
    )

    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("button", { name: "跳过" }))
    await user.click(await screen.findByRole("button", { name: "选择" }))
    await user.click(screen.getByRole("button", { name: "Recommend" }))

    expect(await screen.findByRole("button", { name: "Loading..." })).toBeDisabled()

    resolveRecommendations({
      ok: false,
      status: 500,
      json: () => Promise.resolve({}),
    } as Response)
  })

  it("shows search suggestions when the user types in the search box", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = input.toString()
        if (url.endsWith("/genres")) return jsonResponse([{ name: "Comedy" }])
        if (url.includes("/genres/all/seeds")) return jsonResponse({ seeds: [] })
        if (url.includes("/movies/search")) return jsonResponse([
          { movie_id: 1, title: "Toy Story (1995)" },
          { movie_id: 3114, title: "Toy Story 2 (1999)" },
        ])
        return jsonResponse({})
      })
    )

    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("button", { name: "跳过" }))
    await user.type(screen.getByPlaceholderText("搜索电影..."), "toy")

    expect(await screen.findByText("Toy Story (1995)")).toBeInTheDocument()
    expect(screen.getByText("Toy Story 2 (1999)")).toBeInTheDocument()
  })
})

async function requestRecommendations(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "跳过" }))
  await user.click(await screen.findByRole("button", { name: "选择" }))
  await user.click(screen.getByRole("button", { name: "Recommend" }))
}
