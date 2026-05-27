// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import App from "./App"

const jsonResponse = (payload: unknown) =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve(payload),
  } as Response)

describe("App RAG explanations", () => {
  beforeEach(() => {
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
          return jsonResponse({
            items: [{ movie_id: 239, title: "Some Movie", score: 0.9 }],
            seed_movies: [{ movie_id: 1, title: "Toy Story (1995)" }],
            anchor_source: "seed_set",
            model_version: "test-model",
          })
        }

        if (url.endsWith("/rag/explanations")) {
          return jsonResponse({
            summary: "These picks match your seed set through shared tone and genre signals.",
            items: [
              {
                movie_id: 239,
                reason: "It keeps the same light adventure pattern.",
                evidence: ["seed_set", "content_signal"],
              },
            ],
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
    vi.unstubAllGlobals()
  })

  it("requests and displays the RAG explanation after recommendations are generated", async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("button", { name: "跳过" }))
    await user.click(await screen.findByRole("button", { name: "选择" }))
    await user.click(screen.getByRole("button", { name: "Recommend" }))

    expect(await screen.findByText("These picks match your seed set through shared tone and genre signals.")).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith(
      "http://reco-api:8000/rag/explanations",
      expect.objectContaining({ method: "POST" })
    )
  })
})
