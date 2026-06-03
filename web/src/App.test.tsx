// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest"
import { cleanup, render, screen, waitFor, within } from "@testing-library/react"
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

        if (url.endsWith("/system/evidence")) {
          return jsonResponse({
            system_name: "movie-recommendation-system",
            deployment: {
              platform: "AWS EC2",
              runtime: "Docker Compose",
              ui_url: "http://34.228.75.214:3000",
              api_url: "http://34.228.75.214:8000",
            },
            serving: {
              status: "ok",
              redis_ok: true,
              onnx_ok: true,
              metadata_ok: true,
              model_version: "dev",
            },
            model_truth: {
              product_ranking_path: "Seed Set recommendations driven by Content Signal",
              ncf_onnx_status: "legacy/debug/evaluation path unless later wired into product ranking",
            },
            evaluation: {
              rmse: 3.1438,
              recall_at_k: 0.05,
              ndcg_at_k: 0.0258,
              recommendation_coverage: 0.0287,
              topk_diversity: 0.5997,
              popularity_baseline_recall_at_k: 0.02,
            },
            benchmark: {
              recommendations_p95_ms: 65.459,
              rag_explanations_p95_ms: 5.088,
            },
            rag: {
              public_provider: "mock",
              secret_policy: "real provider keys stay backend-only and are not committed",
            },
          })
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

  it("requests and displays the RAG per-card reason after recommendations are generated", async () => {
    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    expect(await screen.findByText("It keeps the same light adventure pattern.")).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/rag/explanations"),
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

    expect(await screen.findByText("Couldn't load recommendations. Check your connection and try again.")).toBeInTheDocument()
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

    expect((await screen.findAllByText("Some Movie")).length).toBeGreaterThan(0)
    expect(screen.getByText("AI explanation unavailable. Your recommendations are still accurate.")).toBeInTheDocument()
  })

  it("renders per-card reasons on fallback without exposing provider details", async () => {
    ragExplanationSource = "deterministic_fallback"

    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    expect(await screen.findByText("It keeps the same light adventure pattern.")).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: "Why these movies?" })).not.toBeInTheDocument()
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

    const moreRecommendations = screen.getByRole("heading", { name: "More movies you might like" }).closest(".card")
    expect(moreRecommendations).not.toBeNull()
    expect(within(moreRecommendations as HTMLElement).getByText("Fourth Recommendation")).toBeInTheDocument()
    expect(within(moreRecommendations as HTMLElement).queryByText(/AI reason/)).not.toBeInTheDocument()
  })

  it("keeps the selected seed set visible on the recommendation results page", async () => {
    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    const seedBanner = document.querySelector(".seed-banner")
    expect(seedBanner).not.toBeNull()
    expect(within(seedBanner as HTMLElement).getByText("Toy Story (1995)")).toBeInTheDocument()
  })

  it("removes the standalone AI explanation summary and score breakdown from the results page", async () => {
    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    expect(await screen.findByText("It keeps the same light adventure pattern.")).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: "Why these movies?" })).not.toBeInTheDocument()
    expect(screen.queryByText("These picks match your seed set through shared tone and genre signals.")).not.toBeInTheDocument()
    expect(screen.queryByText("Score breakdown")).not.toBeInTheDocument()
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
    expect(within(featured as HTMLElement).queryByText("#2")).not.toBeInTheDocument()
    expect(within(featured as HTMLElement).queryByText("#3")).not.toBeInTheDocument()
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

    await screen.findByText("It keeps the same light adventure pattern.")
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

    await user.click(screen.getByRole("button", { name: "Skip" }))

    const recommendButton = screen.getByRole("button", { name: "Recommend" })
    expect(recommendButton).toBeDisabled()
  })

  it("navigates to step 3 immediately and shows loading state while fetching recommendations", async () => {
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

    await user.click(screen.getByRole("button", { name: "Skip" }))
    await user.click(await screen.findByRole("button", { name: "Select" }))
    await user.click(screen.getByRole("button", { name: "Recommend" }))

    // Step 3 appears immediately — loading subtitle shown before data arrives
    expect(await screen.findByText("Finding your movies…")).toBeInTheDocument()
    // No real movie articles yet — skeleton divs stand in
    expect(screen.queryAllByRole("article")).toHaveLength(0)

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

    await user.click(screen.getByRole("button", { name: "Skip" }))
    await user.type(screen.getByPlaceholderText("Search movies..."), "toy")

    expect(await screen.findByText("Toy Story (1995)")).toBeInTheDocument()
    expect(screen.getByText("Toy Story 2 (1999)")).toBeInTheDocument()
  })

  it("returns to the previous step when the back button is clicked", async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("button", { name: "Skip" }))
    expect(screen.getByText("Select Movies")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Back" }))
    expect(screen.getByText("Select Genres")).toBeInTheDocument()
  })

  it("resets to step one and clears seeds when restart is clicked on results page", async () => {
    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    await user.click(await screen.findByRole("button", { name: "Start over" }))
    expect(screen.getByText("Select Genres")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Skip" }))
    expect(screen.getByText("Selected (0/5):")).toBeInTheDocument()
  })

  it("displays movie titles with leading article moved to the front", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = input.toString()
        if (url.endsWith("/genres")) return jsonResponse([{ name: "Comedy" }])
        if (url.includes("/genres/all/seeds")) return jsonResponse({
          seeds: [
            { movie_id: 357, title: "Lion King, The (1994)" },
            { movie_id: 588, title: "Aladdin (1992)" },
            { movie_id: 3114, title: "Goofy Movie, A (1995)" },
          ],
        })
        if (url.endsWith("/recommendations")) return jsonResponse({
          items: [
            { movie_id: 357, title: "Lion King, The (1994)", score: 0.9 },
            { movie_id: 588, title: "Aladdin (1992)", score: 0.8 },
            { movie_id: 3114, title: "Goofy Movie, A (1995)", score: 0.7 },
          ],
          seed_movies: [{ movie_id: 1, title: "Toy Story (1995)" }],
          anchor_source: "seed",
          model_version: "dev",
        })
        if (url.endsWith("/rag/explanations")) return jsonResponse({
          summary: "Great picks.",
          items: [
            { movie_id: 357, reason: "Reason 1", evidence: ["seed_set"] },
            { movie_id: 588, reason: "Reason 2", evidence: ["seed_set"] },
            { movie_id: 3114, reason: "Reason 3", evidence: ["seed_set"] },
          ],
          explanation_source: "rag",
        })
        if (url.endsWith("/explanations")) return jsonResponse({
          user_id: null, model_version: "dev", alpha: 0.5,
          anchor_movie: null, topk: [], similar_movies: [], content_available: true,
        })
        return jsonResponse({})
      })
    )

    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("button", { name: "Skip" }))

    expect(await screen.findByText("The Lion King (1994)")).toBeInTheDocument()
    expect(screen.queryByText("Lion King, The (1994)")).not.toBeInTheDocument()

    expect(screen.getByText("A Goofy Movie (1995)")).toBeInTheDocument()
    expect(screen.queryByText("Goofy Movie, A (1995)")).not.toBeInTheDocument()

    expect(screen.getByText("Aladdin (1992)")).toBeInTheDocument()

    await user.click(screen.getAllByRole("button", { name: "Select" })[0])
    await user.click(screen.getByRole("button", { name: "Recommend" }))

    expect(await screen.findAllByText("The Lion King (1994)")).not.toHaveLength(0)
    expect(screen.queryByText("Lion King, The (1994)")).not.toBeInTheDocument()
    expect(screen.getAllByText("A Goofy Movie (1995)")).not.toHaveLength(0)
  })

  it("shows English labels on step 1: heading, skip, and next buttons", async () => {
    render(<App />)

    expect(screen.getByRole("heading", { name: "Select Genres" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Skip" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Next" })).toBeInTheDocument()
  })

  it("shows English labels on step 2: heading, search placeholder, select, back, and clear selection", async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("button", { name: "Skip" }))

    expect(screen.getByRole("heading", { name: "Select Movies" })).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Search movies...")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Back" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Clear selection" })).toBeInTheDocument()
  })

  it("shows English labels on step 3: shuffle and start over buttons", async () => {
    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    expect(await screen.findByRole("button", { name: "Shuffle" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Start over" })).toBeInTheDocument()
  })

  it("updates the step indicator as the user progresses through the wizard", async () => {
    const user = userEvent.setup()
    render(<App />)

    expect(screen.getByLabelText("Recommendation steps")).toBeInTheDocument()
    expect(screen.getByText("Genres").closest(".stepper-step")).toHaveClass("active")

    await user.click(screen.getByRole("button", { name: "Skip" }))
    expect(screen.getByText("Movies").closest(".stepper-step")).toHaveClass("active")

    await user.click(await screen.findByRole("button", { name: "Select" }))
    await user.click(screen.getByRole("button", { name: "Recommend" }))

    expect(screen.getByText("Results").closest(".stepper-step")).toHaveClass("active")
    expect(screen.getByText("Results").closest(".stepper-step")).toHaveAttribute("aria-current", "step")
  })

  it("excludes already-selected seeds from search suggestions", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = input.toString()
        if (url.endsWith("/genres")) return jsonResponse([{ name: "Comedy" }])
        if (url.includes("/genres/all/seeds")) return jsonResponse({
          seeds: [{ movie_id: 1, title: "Toy Story (1995)" }],
        })
        if (url.includes("/movies/search")) return jsonResponse([
          { movie_id: 1, title: "Toy Story (1995)" },
          { movie_id: 2, title: "Toy Story 2 (1999)" },
        ])
        return jsonResponse({})
      })
    )

    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("button", { name: "Skip" }))
    await user.click(await screen.findByRole("button", { name: "Select" }))
    expect(screen.getByText("Selected (1/5):")).toBeInTheDocument()

    await user.type(screen.getByPlaceholderText("Search movies..."), "toy")

    const suggestions = await screen.findByText("Toy Story 2 (1999)")
    expect(suggestions).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Toy Story (1995)" })).not.toBeInTheDocument()
  })

  it("clears all seeds and stays on step 2 when Clear selection is clicked", async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("button", { name: "Skip" }))
    await user.click(await screen.findByRole("button", { name: "Select" }))
    expect(screen.getByText("Selected (1/5):")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Clear selection" }))

    expect(screen.getByText("Selected (0/5):")).toBeInTheDocument()
    expect(screen.getByText("Select Movies")).toBeInTheDocument()
  })

  it("removes a seed from the selected list when the × button is clicked", async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("button", { name: "Skip" }))
    await user.click(await screen.findByRole("button", { name: "Select" }))

    expect(screen.getByText("Selected (1/5):")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Remove Toy Story (1995)" })).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Remove Toy Story (1995)" }))

    expect(screen.getByText("Selected (0/5):")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Remove Toy Story (1995)" })).not.toBeInTheDocument()
  })

  it("sends shuffle:true when the user clicks the shuffle button on the results page", async () => {
    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    expect((await screen.findAllByText("Some Movie")).length).toBeGreaterThan(0)

    await user.click(screen.getByRole("button", { name: "Shuffle" }))

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/recommendations"),
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"shuffle":true'),
      })
    )
  })

  it("refetches with year bounds when a results time-range chip is selected", async () => {
    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)
    await screen.findByText("It keeps the same light adventure pattern.")

    await user.click(screen.getByRole("button", { name: "1990s" }))

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/recommendations"),
        expect.objectContaining({ body: expect.stringContaining('"year_min":1990') })
      )
    )
  })

  it("refetches with genres when a results topic chip is selected", async () => {
    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)
    await screen.findByText("It keeps the same light adventure pattern.")

    await user.click(screen.getByRole("button", { name: "Drama" }))

    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/recommendations"),
        expect.objectContaining({ body: expect.stringContaining('"genres":["Drama"]') })
      )
    )
  })

  it("shows a no-match empty state with a reset action when filters return nothing", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = input.toString()
        if (url.endsWith("/genres")) return jsonResponse([{ name: "Comedy" }])
        if (url.includes("/genres/all/seeds")) return jsonResponse({ seeds: [{ movie_id: 1, title: "Toy Story (1995)" }] })
        if (url.endsWith("/recommendations")) {
          return jsonResponse({ items: [], seed_movies: [], anchor_source: "seed", model_version: "dev" })
        }
        if (url.endsWith("/rag/explanations")) return jsonResponse({ summary: "", items: [], explanation_source: "rag" })
        return jsonResponse({})
      })
    )

    const user = userEvent.setup()
    render(<App />)

    await requestRecommendations(user)

    expect(await screen.findByText("No movies match your current filters.")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Reset filters" })).toBeInTheDocument()
  })

  it("fetches seeds filtered by genre when the user selects a genre chip", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = input.toString()
        if (url.endsWith("/genres")) return jsonResponse([{ name: "Comedy" }])
        if (url.includes("/genres/Comedy/seeds")) return jsonResponse({
          seeds: [{ movie_id: 99, title: "Comedy Movie (2000)" }],
        })
        if (url.includes("/genres/all/seeds")) return jsonResponse({ seeds: [] })
        return jsonResponse({})
      })
    )

    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole("button", { name: "Comedy" }))
    await user.click(screen.getByRole("button", { name: "Next" }))

    expect(await screen.findByText("Comedy Movie (2000)")).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/genres/Comedy/seeds")
    )
  })

  it("does not add a sixth seed when the seed limit is already reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = input.toString()
        if (url.endsWith("/genres")) return jsonResponse([{ name: "Comedy" }])
        if (url.includes("/genres/all/seeds")) return jsonResponse({
          seeds: [
            { movie_id: 1, title: "Movie 1" },
            { movie_id: 2, title: "Movie 2" },
            { movie_id: 3, title: "Movie 3" },
            { movie_id: 4, title: "Movie 4" },
            { movie_id: 5, title: "Movie 5" },
            { movie_id: 6, title: "Movie 6" },
          ],
        })
        return jsonResponse({})
      })
    )

    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("button", { name: "Skip" }))

    const selectButtons = await screen.findAllByRole("button", { name: "Select" })
    for (const btn of selectButtons.slice(0, 5)) {
      await user.click(btn)
    }

    expect(screen.getByText("Selected (5/5):")).toBeInTheDocument()

    await user.click(selectButtons[5])
    expect(screen.getByText("Selected (5/5):")).toBeInTheDocument()
  })

  it("loads all genres from the API in a single grid", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = input.toString()
        if (url.endsWith("/genres")) {
          return jsonResponse([
            { name: "Comedy" },
            { name: "Drama" },
            { name: "Action" },
            { name: "Horror" },
            { name: "Sci-Fi" },
          ])
        }
        return jsonResponse({})
      })
    )

    render(<App />)

    expect(await screen.findByRole("button", { name: "Comedy" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Horror" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Sci-Fi" })).toBeInTheDocument()
    expect(screen.getByText("0/3 selected")).toBeInTheDocument()
  })

  it("shows genre error with retry when the genres API fails", async () => {
    vi.useFakeTimers()
    let genreAttempts = 0
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = input.toString()
        if (url.endsWith("/genres")) {
          genreAttempts += 1
          return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) } as Response)
        }
        return jsonResponse({})
      })
    )

    render(<App />)

    await vi.runAllTimersAsync()

    expect(screen.getByRole("alert")).toHaveTextContent(/Could not load genres/i)
    expect(genreAttempts).toBeGreaterThanOrEqual(3)
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument()
    vi.useRealTimers()
  })

  it("renders the System Evidence dashboard without claiming model comparison", async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("button", { name: "System Evidence" }))

    expect(await screen.findByRole("heading", { name: "System Evidence" })).toBeInTheDocument()
    expect(screen.getByText("Serving Health")).toBeInTheDocument()
    expect(screen.getByText("Evaluation Quality")).toBeInTheDocument()
    expect(screen.getByText("Current vs Popularity Baseline")).toBeInTheDocument()
    expect(screen.getByText("Latency Benchmark")).toBeInTheDocument()
    expect(screen.getByText("RAG & Safety")).toBeInTheDocument()
    expect(screen.getByText("AWS EC2 Deployment")).toBeInTheDocument()
    expect(screen.getByText("Seed Set recommendations driven by Content Signal")).toBeInTheDocument()
    expect(screen.getByText("Current Recall@K")).toBeInTheDocument()
    expect(screen.getByText("Popularity Baseline Recall@K")).toBeInTheDocument()
    expect(screen.getByText("0.050")).toBeInTheDocument()
    expect(screen.getByText("0.020")).toBeInTheDocument()
    expect(screen.getByText("Docker Compose")).toBeInTheDocument()
    expect(screen.getByText("mock")).toBeInTheDocument()
    expect(screen.queryByText("Model Comparison")).not.toBeInTheDocument()
  })
})

describe("App movie posters", () => {
  const posterFields = {
    poster_url: "https://image.tmdb.org/t/p/w500/test.jpg",
    poster_thumb_url: "https://image.tmdb.org/t/p/w185/test.jpg",
  }

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = input.toString()

        if (url.endsWith("/genres")) {
          return jsonResponse([{ name: "Comedy" }])
        }
        if (url.includes("/genres/all/seeds")) {
          return jsonResponse({
            seeds: [{ movie_id: 1, title: "Toy Story (1995)", ...posterFields }],
          })
        }
        if (url.includes("/movies/search")) {
          return jsonResponse([{ movie_id: 1, title: "Toy Story (1995)", ...posterFields }])
        }
        if (url.endsWith("/recommendations")) {
          return jsonResponse({
            items: [{ movie_id: 239, title: "Some Movie", score: 0.9, ...posterFields }],
            seed_movies: [{ movie_id: 1, title: "Toy Story (1995)", ...posterFields }],
            anchor_source: "seed",
            model_version: "test-model",
          })
        }
        if (url.endsWith("/explanations")) {
          return jsonResponse({
            user_id: null,
            model_version: "test-model",
            alpha: 0.7,
            anchor_movie: { movie_id: 1, title: "Toy Story (1995)" },
            topk: [{ movie_id: 239, title: "Some Movie", ncf: 0, content: 0.9, final: 0.9 }],
            similar_movies: [],
            content_available: true,
            anchor_source: "seed",
          })
        }
        if (url.endsWith("/rag/explanations")) {
          return jsonResponse({
            summary: "Summary",
            items: [{ movie_id: 239, reason: "Reason", evidence: ["seed_set"] }],
            explanation_source: "rag",
          })
        }
        return jsonResponse({})
      })
    )
  })

  it("renders the TMDB attribution footer", () => {
    render(<App />)
    expect(screen.getByText(/not endorsed or certified by TMDB/i)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "TMDB" })).toHaveAttribute("href", "https://www.themoviedb.org/")
  })

  it("renders featured cards with poster styling when poster_url is present", async () => {
    const user = userEvent.setup()
    render(<App />)
    await requestRecommendations(user)
    const card = await screen.findByRole("heading", { name: "Some Movie" })
    expect(card.closest(".movie-card")).toHaveClass("has-poster")
  })

  it("renders a poster grid for ranked overflow in the More movies section", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = input.toString()
        if (url.endsWith("/genres")) return jsonResponse([{ name: "Comedy" }])
        if (url.includes("/genres/all/seeds")) {
          return jsonResponse({ seeds: [{ movie_id: 1, title: "Toy Story (1995)", ...posterFields }] })
        }
        if (url.endsWith("/recommendations")) {
          return jsonResponse({
            items: [
              { movie_id: 11, title: "First (2001)", score: 0.9, ...posterFields },
              { movie_id: 12, title: "Second (2002)", score: 0.8, ...posterFields },
              { movie_id: 13, title: "Third (2003)", score: 0.7, ...posterFields },
              { movie_id: 14, title: "Fourth (2004)", score: 0.6, ...posterFields },
            ],
            seed_movies: [{ movie_id: 1, title: "Toy Story (1995)", ...posterFields }],
            anchor_source: "seed",
            model_version: "test-model",
          })
        }
        if (url.endsWith("/rag/explanations")) {
          return jsonResponse({ summary: "Summary", items: [], explanation_source: "rag" })
        }
        return jsonResponse({})
      })
    )

    const user = userEvent.setup()
    render(<App />)
    await requestRecommendations(user)

    const moreSection = (await screen.findByRole("heading", { name: "More movies you might like" })).closest(".card")
    expect(moreSection).not.toBeNull()
    const overflowTitle = within(moreSection as HTMLElement).getByText("Fourth (2004)")
    expect(overflowTitle.closest(".poster-tile")).not.toBeNull()
    expect(within(moreSection as HTMLElement).queryByText("0.600")).not.toBeInTheDocument()
  })

  it("renders search suggestion thumbnails when poster_thumb_url is present", async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getAllByRole("button", { name: "Skip" })[0])
    const search = screen.getByPlaceholderText("Search movies...")
    await user.type(search, "Toy")
    const listbox = await screen.findByRole("listbox")
    expect(within(listbox).getByRole("presentation")).toHaveAttribute("src", posterFields.poster_thumb_url)
  })
})

async function requestRecommendations(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Skip" }))
  await user.click(await screen.findByRole("button", { name: "Select" }))
  await user.click(screen.getByRole("button", { name: "Recommend" }))
}
