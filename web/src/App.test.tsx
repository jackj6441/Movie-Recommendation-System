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
