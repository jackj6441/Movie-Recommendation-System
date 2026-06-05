// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest"
import { cleanup, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import App from "./App"
import { buildSseBody, createFetchMock, jsonResponse, sseResponse } from "./test/chatFetchMock"

describe("App conversational RAG chat", () => {
  let chatConfig: Parameters<typeof createFetchMock>[0]

  beforeEach(() => {
    chatConfig = {}
    vi.stubGlobal("fetch", createFetchMock(chatConfig))
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it("renders disambiguation from final-only SSE without stuck loading", async () => {
    chatConfig.needsDisambiguation = true
    chatConfig.needsClarification = true
    chatConfig.finalOnly = true
    chatConfig.assistantMessage = "Pick a starting movie from the list below."
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)

    await user.type(
      await screen.findByPlaceholderText("Describe the kind of movies you want…"),
      "zzzznotamovie"
    )
    await user.click(screen.getByRole("button", { name: "Send" }))

    expect(await screen.findByText("Pick a starting movie from the list below.")).toBeInTheDocument()
    expect(screen.queryByText("…")).not.toBeInTheDocument()
    expect(await screen.findByText(/Which movie did you mean\?/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Send" })).toBeEnabled()
  })

  it("shows disambiguation candidate year in picker rows", async () => {
    chatConfig.needsDisambiguation = true
    chatConfig.needsClarification = true
    chatConfig.finalOnly = true
    chatConfig.disambiguationCandidates = [
      { movie_id: 50, title: "King Kong", year: 2005, genres: ["Adventure"] },
    ]
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)
    await user.type(
      await screen.findByPlaceholderText("Describe the kind of movies you want…"),
      "king kong"
    )
    await user.click(screen.getByRole("button", { name: "Send" }))

    expect(await screen.findByText("King Kong (2005)")).toBeInTheDocument()
    expect(screen.getByText("Adventure")).toBeInTheDocument()
  })

  it("submits disambiguation picks with replace seed mode", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }])
      }
      if (url.endsWith("/rag/chat")) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        if (body.seed_movie_ids) {
          expect(body.seed_update_mode).toBe("replace")
          expect(body.seed_movie_ids).toEqual([50])
          return sseResponse(
            buildSseBody({
              assistantMessage: "Recommendations after your pick.",
            })
          )
        }
        return sseResponse(
          buildSseBody({
            needsClarification: true,
            needsDisambiguation: true,
            assistantMessage: "Pick a starting movie.",
          })
        )
      }
      throw new Error(`Unhandled: ${url}`)
    })
    vi.stubGlobal("fetch", fetchMock)

    const user = userEvent.setup()
    render(<App />)

    await user.type(
      await screen.findByPlaceholderText("Describe the kind of movies you want…"),
      "zzzznotamovie"
    )
    await user.click(screen.getByRole("button", { name: "Send" }))
    expect(await screen.findByText(/Which movie did you mean\?/)).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: /Candidate Movie/i }))
    await user.click(screen.getByRole("button", { name: "Use as Seed Set" }))

    expect(await screen.findByText("Recommendations after your pick.")).toBeInTheDocument()
    expect(await screen.findByText("You picked: Candidate Movie (2000)")).toBeInTheDocument()
  })

  it("more like this sends append seed chat turn", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }])
      }
      if (url.endsWith("/rag/chat")) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        if (body.seed_movie_ids?.length === 1 && body.seed_update_mode === "append") {
          return sseResponse(
            buildSseBody({
              assistantMessage: "More like that pick.",
              items: [{ movie_id: 55, title: "Similar (2010)", score: 0.8 }],
            })
          )
        }
        return sseResponse(buildSseBody({ assistantMessage: "First list." }))
      }
      throw new Error(`Unhandled: ${url}`)
    })
    vi.stubGlobal("fetch", fetchMock)

    const user = userEvent.setup()
    render(<App />)
    await sendChat(user, "first")

    await user.click(screen.getByRole("button", { name: "More like this" }))
    expect(await screen.findByText("More like that pick.")).toBeInTheDocument()
    expect(await screen.findByText("More like: Some Movie (1999)")).toBeInTheDocument()
  })

  it("shows current taste chips after recommendations", async () => {
    chatConfig.assistantMessage = "Done."
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)
    await sendChat(user, "go")

    const taste = document.querySelector("aside.taste-rail--desktop") as HTMLElement
    expect(taste).not.toBeNull()
    expect(within(taste).getByText("Comedy")).toBeInTheDocument()
    expect(within(taste).getByText("Toy Story (1995)")).toBeInTheDocument()
  })

  it("renders desktop taste rail aside when thread has context", async () => {
    chatConfig.assistantMessage = "Done."
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)
    await sendChat(user, "go")

    const rail = document.querySelector("aside.taste-rail--desktop")
    expect(rail).not.toBeNull()
    expect(rail).toHaveAttribute("aria-label", "Current taste")
    expect(document.querySelector(".chat-layout--with-rail")).not.toBeNull()
  })

  it("renders poster-forward disambiguation grid", async () => {
    chatConfig.needsDisambiguation = true
    chatConfig.needsClarification = true
    chatConfig.finalOnly = true
    chatConfig.disambiguationCandidates = [
      {
        movie_id: 50,
        title: "King Kong",
        year: 2005,
        genres: ["Adventure"],
        poster_url: "https://image.tmdb.org/t/p/w500/poster.jpg",
      },
    ]
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)
    await user.type(
      await screen.findByPlaceholderText("Describe the kind of movies you want…"),
      "kong"
    )
    await user.click(screen.getByRole("button", { name: "Send" }))

    expect(document.querySelector(".disambiguation-picker-grid")).not.toBeNull()
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: /King Kong/i })).toBeInTheDocument()
  })

  it("scrolls to latest assistant bubble after more like this", async () => {
    const scrollIntoView = vi.fn()
    Element.prototype.scrollIntoView = scrollIntoView

    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }])
      }
      if (url.endsWith("/rag/chat")) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        if (body.seed_movie_ids?.length === 1 && body.seed_update_mode === "append") {
          return sseResponse(
            buildSseBody({
              assistantMessage: "More like that pick.",
              items: [{ movie_id: 55, title: "Similar (2010)", score: 0.8 }],
            })
          )
        }
        return sseResponse(buildSseBody({ assistantMessage: "First list." }))
      }
      throw new Error(`Unhandled: ${url}`)
    })
    vi.stubGlobal("fetch", fetchMock)

    const user = userEvent.setup()
    render(<App />)
    await sendChat(user, "first")
    await user.click(screen.getByRole("button", { name: "More like this" }))
    await screen.findByText("More like that pick.")

    await waitFor(() => {
      expect(scrollIntoView).toHaveBeenCalled()
    })
  })

  it("sends refresh turn when session already has seeds", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }])
      }
      if (url.endsWith("/rag/chat")) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        if (body.session_id) {
          expect(body.message).toBe("")
          expect(body.genres).toEqual([])
          return sseResponse(
            buildSseBody({
              assistantMessage: "Refreshed list.",
              seedMovies: [{ movie_id: 1, title: "Toy Story (1995)" }],
            })
          )
        }
        return sseResponse(
          buildSseBody({
            assistantMessage: "First list.",
            seedMovies: [{ movie_id: 1, title: "Toy Story (1995)" }],
          })
        )
      }
      throw new Error(`Unhandled: ${url}`)
    })
    vi.stubGlobal("fetch", fetchMock)

    const user = userEvent.setup()
    render(<App />)
    await sendChat(user, "first")

    const genreRow = screen.getByRole("group", { name: "Genre filters" })
    await user.click(within(genreRow).getByRole("button", { name: "Comedy" }))
    const send = screen.getByRole("button", { name: "Send" })
    expect(send).toBeEnabled()
    await user.click(send)

    expect(await screen.findByText("Show more recommendations.")).toBeInTheDocument()
    expect(await screen.findByText("Refreshed list.")).toBeInTheDocument()
  })

  it("sends genre-only turn with empty message and shows user summary", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }])
      }
      if (url.endsWith("/rag/chat")) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        expect(body.message).toBe("")
        expect(body.genres).toEqual(["Comedy"])
        return sseResponse(
          buildSseBody({
            assistantMessage: "Comedy picks for you.",
          })
        )
      }
      throw new Error(`Unhandled: ${url}`)
    })
    vi.stubGlobal("fetch", fetchMock)

    const user = userEvent.setup()
    render(<App />)

    const send = await screen.findByRole("button", { name: "Send" })
    await user.click(await screen.findByRole("button", { name: "Comedy" }))
    expect(send).toBeEnabled()
    await user.click(send)

    expect(await screen.findByText("You selected: Comedy")).toBeInTheDocument()
    expect(await screen.findByText("Comedy picks for you.")).toBeInTheDocument()
  })

  it("posts to /rag/chat and shows assistant message with recommendations", async () => {
    chatConfig.assistantMessage = "Here are comedies you might enjoy tonight."
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole("button", { name: "Comedy" }))
    await user.type(
      await screen.findByPlaceholderText("Describe the kind of movies you want…"),
      "something light"
    )
    await user.click(screen.getByRole("button", { name: "Send" }))

    expect(await screen.findByText("Here are comedies you might enjoy tonight.")).toBeInTheDocument()
    expect(await screen.findByRole("heading", { name: "Some Movie (1999)" })).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/rag/chat"),
      expect.objectContaining({ method: "POST" })
    )
    expect(fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/rag/explanations"),
      expect.anything()
    )
  })

  it("shows clarification without recommendation cards when the backend asks", async () => {
    chatConfig.needsClarification = true
    chatConfig.assistantMessage = "Pick a genre or name a movie you like."
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)

    await user.type(
      screen.getByPlaceholderText("Describe the kind of movies you want…"),
      "surprise me"
    )
    await user.click(screen.getByRole("button", { name: "Send" }))

    expect(await screen.findByText("Pick a genre or name a movie you like.")).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: "Some Movie" })).not.toBeInTheDocument()
  })

  it("keeps the composer usable when chat request fails", async () => {
    chatConfig.chatOk = false
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole("button", { name: "Comedy" }))
    await user.type(
      await screen.findByPlaceholderText("Describe the kind of movies you want…"),
      "go"
    )
    await user.click(screen.getByRole("button", { name: "Send" }))

    expect(
      await screen.findByText("Couldn't complete that request. Check your connection and try again.")
    ).toBeInTheDocument()
    await user.type(
      await screen.findByPlaceholderText("Describe the kind of movies you want…"),
      "try again"
    )
    expect(screen.getByRole("button", { name: "Send" })).toBeEnabled()
  })

  it("reuses session_id on follow-up messages", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }])
      }
      if (url.endsWith("/rag/chat")) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        const session = body.session_id ?? null
        return sseResponse(
          buildSseBody({
            assistantMessage: session ? "Follow-up reply" : "First reply",
            items: [{ movie_id: 101, title: "First Movie (2001)", score: 0.9 }],
          })
        )
      }
      throw new Error(`Unhandled: ${url}`)
    })
    vi.stubGlobal("fetch", fetchMock)

    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole("button", { name: "Comedy" }))
    const input = await screen.findByPlaceholderText("Describe the kind of movies you want…")
    await user.type(input, "first")
    await user.click(screen.getByRole("button", { name: "Send" }))
    await screen.findByText("First reply")

    await user.type(input, "second")
    await user.click(screen.getByRole("button", { name: "Send" }))
    expect(await screen.findByText("Follow-up reply")).toBeInTheDocument()

    const chatCalls = (fetch as ReturnType<typeof vi.fn>).mock.calls.filter((call) =>
      String(call[0]).endsWith("/rag/chat")
    )
    expect(chatCalls.length).toBe(2)
    const secondBody = JSON.parse(String((chatCalls[1][1] as RequestInit).body))
    expect(secondBody.session_id).toBe("sess-test-1")
  })

  it("renders hero plus nine more movies when chat returns ten items", async () => {
    chatConfig.items = Array.from({ length: 10 }, (_, index) => ({
      movie_id: 100 + index,
      title: `Ranked Film ${index + 1} (2001)`,
      score: 0.95 - index * 0.01,
    }))
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)
    await sendChat(user, "ten picks")

    expect(await screen.findByRole("heading", { name: "Ranked Film 1 (2001)" })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "More movies you might like" })).toBeInTheDocument()
    expect(screen.getByText("Ranked Film 10 (2001)")).toBeInTheDocument()
  })

  it("shows empty recommendations guidance without a hero pick", async () => {
    chatConfig.needsClarification = true
    chatConfig.emptyRecommendations = true
    chatConfig.clarificationReason = "empty_recommendations"
    chatConfig.assistantMessage =
      "No recommendations matched your current filters. Try removing the year filter or selecting fewer genres."
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)
    await sendChat(user, "too strict")

    expect(
      await screen.findByText(/No recommendations matched your current filters/i)
    ).toBeInTheDocument()
    expect(
      screen.getByText(/No movies matched that request/i)
    ).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: "Some Movie (1999)" })).not.toBeInTheDocument()
  })

  it("renders overflow titles in a poster grid", async () => {
    chatConfig.items = [
      { movie_id: 11, title: "First (2001)", score: 0.9 },
      { movie_id: 12, title: "Second (2002)", score: 0.8 },
      { movie_id: 13, title: "Third (2003)", score: 0.7 },
      { movie_id: 14, title: "Fourth (2004)", score: 0.6 },
    ]
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)

    await sendChat(user, "more")

    expect(await screen.findByRole("heading", { name: "More movies you might like" })).toBeInTheDocument()
    const grid = document.querySelector(".more-movies-grid")
    expect(grid).not.toBeNull()
    expect(within(grid as HTMLElement).getByText("Fourth (2004)")).toBeInTheDocument()
  })

  it("renders the System Evidence dashboard", async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("button", { name: "System Evidence" }))

    expect(await screen.findByRole("heading", { name: "System Evidence" })).toBeInTheDocument()
    expect(screen.getByText("RAG chat p95")).toBeInTheDocument()
    expect(screen.queryByText("Model Comparison")).not.toBeInTheDocument()
  })

  it("renders the TMDB attribution footer", () => {
    render(<App />)
    expect(screen.getByText(/not endorsed or certified by TMDB/i)).toBeInTheDocument()
  })

  it("renders featured hero with poster styling when poster_url is present", async () => {
    const posterUrl = "https://image.tmdb.org/t/p/w500/test.jpg"
    chatConfig.items = [
      { movie_id: 239, title: "Some Movie", score: 0.9, poster_url: posterUrl },
    ]
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)
    await sendChat(user, "show posters")

    const card = await screen.findByRole("heading", { name: "Some Movie" })
    await waitFor(() => {
      expect(card.closest(".hero-pick")).toHaveClass("has-poster")
    })
  })
})

async function sendChat(user: ReturnType<typeof userEvent.setup>, message: string) {
  await user.click(await screen.findByRole("button", { name: "Comedy" }))
  await user.type(
    await screen.findByPlaceholderText("Describe the kind of movies you want…"),
    message
  )
  await user.click(screen.getByRole("button", { name: "Send" }))
}
