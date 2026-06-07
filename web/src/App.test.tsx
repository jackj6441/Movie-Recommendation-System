// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest"
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import App from "./App"
import { buildSseBody, createFetchMock, jsonResponse, sseResponse } from "./test/chatFetchMock"
import { stubLocalStorage } from "./test/localStorageMock"

describe("App conversational RAG chat", () => {
  let chatConfig: Parameters<typeof createFetchMock>[0]

  beforeEach(() => {
    chatConfig = {}
    stubLocalStorage()
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
    expect(screen.getByRole("button", { name: "Use as Seed Set" })).toBeInTheDocument()
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

  it("submits disambiguation genre pick immediately", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }, { name: "Drama" }])
      }
      if (url.endsWith("/rag/chat")) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        if (body.disambiguation_genre === "Drama") {
          return sseResponse(
            buildSseBody({
              assistantMessage: "Drama picks for you.",
              contextGenres: ["Drama"],
              contextSeeds: [],
            })
          )
        }
        return sseResponse(
          buildSseBody({
            needsClarification: true,
            needsDisambiguation: true,
            clarificationReason: "ambiguous_message",
            assistantMessage: "Genre or movie?",
            disambiguationCandidates: [
              {
                movie_id: 7316,
                title: "Confessions of a Teenage Drama Queen (2004)",
                genres: ["Comedy"],
              },
            ],
            disambiguationGenreOptions: ["Drama"],
            contextSeeds: [],
            contextGenres: [],
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
      "drama"
    )
    await user.click(screen.getByRole("button", { name: "Send" }))

    await user.click(screen.getByRole("button", { name: "Drama" }))
    expect(await screen.findByText("Drama picks for you.")).toBeInTheDocument()
    const thread = await screen.findByRole("log")
    expect(within(thread).getByText("You selected: Drama (genre)")).toBeInTheDocument()
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
    expect(screen.getByRole("button", { name: "Use as Seed Set" })).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: /Candidate Movie/i }))
    await user.click(screen.getByRole("button", { name: "Use as Seed Set" }))

    expect(await screen.findByText("Recommendations after your pick.")).toBeInTheDocument()
    const thread = await screen.findByRole("log")
    expect(within(thread).getByText("You picked: Candidate Movie (2000)")).toBeInTheDocument()
  })

  it("clicking hero card sends append seed chat turn", async () => {
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
              assistantMessage: "Updated picks.",
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

    await user.click(
      screen.getByRole("button", { name: "Add Some Movie (1999) to starting movies" })
    )
    expect(await screen.findByText("Updated picks.")).toBeInTheDocument()
    const thread = await screen.findByRole("log")
    expect(within(thread).getByText("Added Some Movie (1999)")).toBeInTheDocument()
  })

  it("clicking strip card sends append seed chat turn", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }])
      }
      if (url.endsWith("/rag/chat")) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        if (body.seed_movie_ids?.[0] === 240 && body.seed_update_mode === "append") {
          return sseResponse(
            buildSseBody({
              assistantMessage: "Strip pick added.",
              items: [{ movie_id: 55, title: "Similar (2010)", score: 0.8 }],
            })
          )
        }
        return sseResponse(
          buildSseBody({
            assistantMessage: "First list.",
            items: [
              { movie_id: 239, title: "Some Movie (1999)", score: 0.9 },
              { movie_id: 240, title: "Strip Movie (2001)", score: 0.85 },
            ],
          })
        )
      }
      throw new Error(`Unhandled: ${url}`)
    })
    vi.stubGlobal("fetch", fetchMock)

    const user = userEvent.setup()
    render(<App />)
    await sendChat(user, "first")

    await user.click(
      screen.getByRole("button", { name: "Add Strip Movie (2001) to starting movies" })
    )
    expect(await screen.findByText("Strip pick added.")).toBeInTheDocument()
  })

  it("ignores append when recommendation is already in seeds", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }])
      }
      if (url.endsWith("/rag/chat")) {
        return sseResponse(
          buildSseBody({
            assistantMessage: "First list.",
            contextSeeds: [
              { movie_id: 1, title: "Toy Story (1995)" },
              { movie_id: 239, title: "Some Movie (1999)" },
            ],
            items: [{ movie_id: 239, title: "Some Movie (1999)", score: 0.9 }],
          })
        )
      }
      throw new Error(`Unhandled: ${url}`)
    })
    vi.stubGlobal("fetch", fetchMock)

    const user = userEvent.setup()
    render(<App />)
    await sendChat(user, "first")

    const chatCallsBefore = fetchMock.mock.calls.filter((call) =>
      String(call[0]).endsWith("/rag/chat")
    ).length
    expect(
      screen.queryByRole("button", { name: "Add Some Movie (1999) to starting movies" })
    ).not.toBeInTheDocument()

    await user.click(screen.getByLabelText("Some Movie (1999) is in your starting movies"))
    const chatCallsAfter = fetchMock.mock.calls.filter((call) =>
      String(call[0]).endsWith("/rag/chat")
    ).length
    expect(chatCallsAfter).toBe(chatCallsBefore)
  })

  it("disables strip add buttons when seed set is full", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }])
      }
      if (url.endsWith("/rag/chat")) {
        return sseResponse(
          buildSseBody({
            assistantMessage: "Full seeds.",
            contextSeeds: [
              { movie_id: 1, title: "Toy Story (1995)" },
              { movie_id: 2, title: "Jumanji (1995)" },
              { movie_id: 3, title: "Grumpier Old Men (1995)" },
              { movie_id: 4, title: "Waiting to Exhale (1995)" },
              { movie_id: 5, title: "Father of the Bride Part II (1995)" },
            ],
            items: [
              { movie_id: 239, title: "Some Movie (1999)", score: 0.9 },
              { movie_id: 240, title: "Strip Movie (2001)", score: 0.85 },
            ],
          })
        )
      }
      throw new Error(`Unhandled: ${url}`)
    })
    vi.stubGlobal("fetch", fetchMock)

    const user = userEvent.setup()
    render(<App />)
    await sendChat(user, "first")

    const heroButton = screen.getByRole("button", {
      name: "Add Some Movie (1999) to starting movies",
    })
    const stripButton = screen.getByRole("button", {
      name: "Add Strip Movie (2001) to starting movies",
    })
    expect(heroButton).toBeDisabled()
    expect(stripButton).toBeDisabled()
    expect(heroButton).toHaveAttribute("title", "Seed set full (max 5)")
    expect(stripButton).toHaveAttribute("title", "Seed set full (max 5)")

    const chatCallsBefore = fetchMock.mock.calls.filter((call) =>
      String(call[0]).endsWith("/rag/chat")
    ).length
    await user.click(heroButton)
    await user.click(stripButton)
    const chatCallsAfter = fetchMock.mock.calls.filter((call) =>
      String(call[0]).endsWith("/rag/chat")
    ).length
    expect(chatCallsAfter).toBe(chatCallsBefore)
  })

  it("shows current taste chips after recommendations", async () => {
    chatConfig.assistantMessage = "Done."
    chatConfig.contextSeeds = [
      {
        movie_id: 1,
        title: "Toy Story (1995)",
        poster_thumb_url: "https://image.tmdb.org/t/p/w185/poster.jpg",
      },
    ]
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)
    await sendChat(user, "go")

    const taste = document.querySelector("aside.taste-rail--desktop") as HTMLElement
    expect(taste).not.toBeNull()
    expect(within(taste).getByText("Comedy")).toBeInTheDocument()
    expect(within(taste).getByText("Toy Story (1995)")).toBeInTheDocument()
    expect(within(taste).queryByRole("button", { name: "Toy Story (1995)" })).toBeNull()
    expect(taste.querySelector(".taste-seed-tile__poster-wrap")).toBeInTheDocument()
    expect(
      taste.querySelector('img[src="https://image.tmdb.org/t/p/w185/poster.jpg"]')
    ).toBeInTheDocument()
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
    expect(document.querySelector(".chat-app-layout--three-col")).not.toBeNull()
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

  it("scrolls to latest assistant bubble after adding seed from hero", async () => {
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
    await user.click(
      screen.getByRole("button", { name: "Add Some Movie (1999) to starting movies" })
    )
    await screen.findByText("More like that pick.")

    await waitFor(() => {
      expect(scrollIntoView).toHaveBeenCalled()
    })
  })

  it("scrolls to latest assistant bubble after disambiguation submit", async () => {
    const scrollIntoView = vi.fn()
    Element.prototype.scrollIntoView = scrollIntoView

    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }])
      }
      if (url.endsWith("/rag/chat")) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        if (body.seed_movie_ids) {
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
    await screen.findByRole("button", { name: "Use as Seed Set" })

    scrollIntoView.mockClear()
    await user.click(screen.getByRole("button", { name: /Candidate Movie/i }))
    await user.click(screen.getByRole("button", { name: "Use as Seed Set" }))
    await screen.findByText("Recommendations after your pick.")

    await waitFor(() => {
      expect(scrollIntoView).toHaveBeenCalled()
    })
  })

  it("scrolls when jumping to a turn from the session sidebar", async () => {
    const scrollIntoView = vi.fn()
    Element.prototype.scrollIntoView = scrollIntoView

    chatConfig.assistantMessage = "First list."
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)
    await sendChat(user, "first message")
    await screen.findByText("First list.")

    const turnList = document.querySelector(".chat-session-turn-list") as HTMLElement
    scrollIntoView.mockClear()
    await user.click(within(turnList).getByRole("button", { name: "first message" }))

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

    expect(screen.queryByRole("group", { name: "Genre filters" })).not.toBeInTheDocument()
    const send = screen.getByRole("button", { name: "Send" })
    expect(send).toBeEnabled()
    await user.click(send)

    const thread = await screen.findByRole("log")
    expect(within(thread).getByText("Show more recommendations.")).toBeInTheDocument()
    expect(within(thread).getByText("Refreshed list.")).toBeInTheDocument()
  })

  it("shows genres edit control in taste rail after first turn", async () => {
    chatConfig.assistantMessage = "First list."
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)
    await sendChat(user, "first")

    expect(screen.queryByRole("group", { name: "Genre filters" })).not.toBeInTheDocument()
    const taste = document.querySelector("aside.taste-rail--desktop") as HTMLElement
    expect(within(taste).getByRole("heading", { name: "Genres" })).toBeInTheDocument()
    expect(within(taste).getAllByRole("button", { name: "Edit" }).length).toBeGreaterThanOrEqual(1)
    const composer = document.querySelector(".chat-composer-wrap") as HTMLElement
    expect(within(composer).queryByRole("group", { name: "Edit genres for this chat" })).not.toBeInTheDocument()
  })

  it("adds genre from taste rail and re-ranks", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }, { name: "Drama" }])
      }
      if (url.endsWith("/rag/chat")) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        if (body.genres?.includes("Drama")) {
          return sseResponse(
            buildSseBody({
              assistantMessage: "Comedy and Drama picks.",
              contextSeeds: [],
              contextGenres: ["Comedy", "Drama"],
              yearMin: 2005,
            })
          )
        }
        return sseResponse(
          buildSseBody({
            assistantMessage: "Comedy picks for you.",
            contextSeeds: [],
            contextGenres: ["Comedy"],
            yearMin: 2005,
          })
        )
      }
      throw new Error(`Unhandled: ${url}`)
    })
    vi.stubGlobal("fetch", fetchMock)

    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole("button", { name: "Comedy" }))
    await user.click(screen.getByRole("button", { name: "Send" }))
    await screen.findByText("Comedy picks for you.")

    const taste = document.querySelector("aside.taste-rail--desktop") as HTMLElement
    const genreSection = within(taste).getByRole("heading", { name: "Genres" }).closest("section") as HTMLElement
    await user.click(within(genreSection).getByRole("button", { name: "Edit" }))
    const editRow = await within(genreSection).findByRole("group", {
      name: "Edit genres for this chat",
    })
    await user.click(within(editRow).getByRole("button", { name: "Drama" }))

    expect(await screen.findByText("Comedy and Drama picks.")).toBeInTheDocument()
    expect(within(taste).getByText("Drama")).toBeInTheDocument()
  })

  it("edit genres panel adds genre with distinct aria label", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }, { name: "Drama" }])
      }
      if (url.endsWith("/rag/chat")) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        if (body.genres?.includes("Drama")) {
          return sseResponse(
            buildSseBody({
              assistantMessage: "Added Drama.",
              contextSeeds: [],
              contextGenres: ["Comedy", "Drama"],
            })
          )
        }
        return sseResponse(
          buildSseBody({
            assistantMessage: "Comedy picks.",
            contextSeeds: [],
            contextGenres: ["Comedy"],
          })
        )
      }
      throw new Error(`Unhandled: ${url}`)
    })
    vi.stubGlobal("fetch", fetchMock)

    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole("button", { name: "Comedy" }))
    await user.click(screen.getByRole("button", { name: "Send" }))
    await screen.findByText("Comedy picks.")

    const taste = document.querySelector("aside.taste-rail--desktop") as HTMLElement
    const genreSection = within(taste).getByRole("heading", { name: "Genres" }).closest("section") as HTMLElement
    await user.click(within(genreSection).getByRole("button", { name: "Edit" }))
    const editRow = await within(genreSection).findByRole("group", {
      name: "Edit genres for this chat",
    })
    await user.click(within(editRow).getByRole("button", { name: "Drama" }))

    const thread = screen.getByRole("log")
    await waitFor(() => {
      expect(within(thread).getAllByText("Added Drama.").length).toBeGreaterThanOrEqual(1)
    })
    expect(screen.queryByRole("group", { name: "Genre filters" })).not.toBeInTheDocument()
  })

  it("genre-only taste rail shows genres only not bootstrap seeds", async () => {
    chatConfig.contextSeeds = []
    chatConfig.contextGenres = ["Comedy"]
    chatConfig.yearMin = 2005
    chatConfig.recencyOptOut = false
    chatConfig.assistantMessage = "Comedy picks for you."
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole("button", { name: "Comedy" }))
    await user.click(screen.getByRole("button", { name: "Send" }))

    expect(await screen.findByText("Comedy picks for you.")).toBeInTheDocument()

    const taste = document.querySelector("aside.taste-rail--desktop") as HTMLElement
    expect(taste).not.toBeNull()
    expect(within(taste).getByText("Comedy")).toBeInTheDocument()
    expect(within(taste).getByText("2005–2025")).toBeInTheDocument()
    expect(within(taste).queryByText("Toy Story (1995)")).not.toBeInTheDocument()
    expect(within(taste).getByRole("heading", { name: "Starting movies" })).toBeInTheDocument()
    expect(within(taste).getByText("None yet")).toBeInTheDocument()
  })

  it("any year pill clears year filter and re-ranks", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }])
      }
      if (url.endsWith("/rag/chat")) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        if (body.clear_year_bounds) {
          expect(body.message).toBe("")
          return sseResponse(
            buildSseBody({
              assistantMessage: "Including older movies now.",
              contextSeeds: [],
              contextGenres: ["Comedy"],
              yearMin: null,
              yearMax: null,
              recencyOptOut: true,
            })
          )
        }
        return sseResponse(
          buildSseBody({
            assistantMessage: "Comedy picks for you.",
            contextSeeds: [],
            contextGenres: ["Comedy"],
            yearMin: 2005,
            yearMax: null,
            recencyOptOut: false,
          })
        )
      }
      throw new Error(`Unhandled: ${url}`)
    })
    vi.stubGlobal("fetch", fetchMock)

    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole("button", { name: "Comedy" }))
    await user.click(screen.getByRole("button", { name: "Send" }))
    await screen.findByText("Comedy picks for you.")

    const taste = document.querySelector("aside.taste-rail--desktop") as HTMLElement
    const yearSection = within(taste)
      .getByRole("heading", { name: "Release year" })
      .closest("section") as HTMLElement
    await user.click(within(yearSection).getByRole("button", { name: "Edit" }))
    await user.click(within(yearSection).getByRole("button", { name: "Any year" }))

    expect(await screen.findByText("Including older movies now.")).toBeInTheDocument()
    await user.click(within(yearSection).getByRole("button", { name: "Edit" }))
    expect(within(yearSection).getByText("Any year")).toBeInTheDocument()
    expect(within(yearSection).queryByText("2005–2025")).not.toBeInTheDocument()
  })

  it("slider drag after any year commits a year range", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }])
      }
      if (url.endsWith("/rag/chat")) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        if (body.clear_year_bounds) {
          return sseResponse(
            buildSseBody({
              assistantMessage: "Including older movies now.",
              contextSeeds: [],
              contextGenres: ["Comedy"],
              yearMin: null,
              yearMax: null,
              recencyOptOut: true,
            })
          )
        }
        if (body.year_min === 1990 && body.year_max === 2004) {
          return sseResponse(
            buildSseBody({
              assistantMessage: "Back to a specific range.",
              contextSeeds: [],
              contextGenres: ["Comedy"],
              yearMin: 1990,
              yearMax: 2004,
              recencyOptOut: false,
            })
          )
        }
        return sseResponse(
          buildSseBody({
            assistantMessage: "Comedy picks for you.",
            contextSeeds: [],
            contextGenres: ["Comedy"],
            yearMin: 2005,
            yearMax: null,
            recencyOptOut: false,
          })
        )
      }
      throw new Error(`Unhandled: ${url}`)
    })
    vi.stubGlobal("fetch", fetchMock)

    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole("button", { name: "Comedy" }))
    await user.click(screen.getByRole("button", { name: "Send" }))
    await screen.findByText("Comedy picks for you.")

    const taste = document.querySelector("aside.taste-rail--desktop") as HTMLElement
    const yearSection = within(taste)
      .getByRole("heading", { name: "Release year" })
      .closest("section") as HTMLElement
    await user.click(within(yearSection).getByRole("button", { name: "Edit" }))
    await user.click(within(yearSection).getByRole("button", { name: "Any year" }))
    await screen.findByText("Including older movies now.")

    const minThumb = within(yearSection).getByLabelText("Release year minimum")
    fireEvent.mouseDown(minThumb)
    fireEvent.change(minThumb, { target: { value: "1990" } })
    const maxThumb = within(yearSection).getByLabelText("Release year maximum")
    fireEvent.change(maxThumb, { target: { value: "2004" } })
    fireEvent.mouseUp(maxThumb)

    await waitFor(() => {
      expect(screen.getByText("Back to a specific range.")).toBeInTheDocument()
    })
    const chatCalls = fetchMock.mock.calls.filter((call) =>
      String(call[0]).endsWith("/rag/chat")
    )
    const lastBody = JSON.parse(String((chatCalls.at(-1)?.[1] as RequestInit)?.body))
    expect(lastBody.year_min).toBe(1990)
    expect(lastBody.year_max).toBe(2004)
    expect(lastBody.clear_year_bounds).toBe(false)
  })

  it("commits explicit year bounds from the release year slider", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString()
      if (url.endsWith("/genres")) {
        return jsonResponse([{ name: "Comedy" }])
      }
      if (url.endsWith("/rag/chat")) {
        const body = init?.body ? JSON.parse(String(init.body)) : {}
        if (body.year_min === 1990 && body.year_max === 2004) {
          return sseResponse(
            buildSseBody({
              assistantMessage: "Nineties picks.",
              contextSeeds: [],
              contextGenres: ["Comedy"],
              yearMin: 1990,
              yearMax: 2004,
              recencyOptOut: false,
            })
          )
        }
        return sseResponse(
          buildSseBody({
            assistantMessage: "Comedy picks for you.",
            contextSeeds: [],
            contextGenres: ["Comedy"],
            yearMin: 2005,
            yearMax: null,
            recencyOptOut: false,
          })
        )
      }
      throw new Error(`Unhandled: ${url}`)
    })
    vi.stubGlobal("fetch", fetchMock)

    const user = userEvent.setup()
    render(<App />)

    await user.click(await screen.findByRole("button", { name: "Comedy" }))
    await user.click(screen.getByRole("button", { name: "Send" }))
    await screen.findByText("Comedy picks for you.")

    const taste = document.querySelector("aside.taste-rail--desktop") as HTMLElement
    const yearSection = within(taste)
      .getByRole("heading", { name: "Release year" })
      .closest("section") as HTMLElement
    await user.click(within(yearSection).getByRole("button", { name: "Edit" }))

    const minThumb = within(yearSection).getByLabelText("Release year minimum")
    fireEvent.mouseDown(minThumb)
    fireEvent.change(minThumb, { target: { value: "1990" } })
    const maxThumb = within(yearSection).getByLabelText("Release year maximum")
    fireEvent.change(maxThumb, { target: { value: "2004" } })
    fireEvent.mouseUp(maxThumb)

    await waitFor(() => {
      expect(screen.getByText("Nineties picks.")).toBeInTheDocument()
    })
    const chatCalls = fetchMock.mock.calls.filter((call) =>
      String(call[0]).endsWith("/rag/chat")
    )
    const lastBody = JSON.parse(String((chatCalls.at(-1)?.[1] as RequestInit)?.body))
    expect(lastBody.year_min).toBe(1990)
    expect(lastBody.year_max).toBe(2004)
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

    const thread = await screen.findByRole("log")
    expect(within(thread).getByText("You selected: Comedy")).toBeInTheDocument()
    expect(within(thread).getByText("Comedy picks for you.")).toBeInTheDocument()
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

  it("renders hero plus scrollable film strip when chat returns ten items", async () => {
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
    expect(screen.getByText("Ranked Film 6 (2001)")).toBeInTheDocument()
    expect(screen.getByText("Ranked Film 10 (2001)")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Show \d+ more/ })).not.toBeInTheDocument()
    expect(document.querySelector(".more-movies-strip-scroller.is-scrollable")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Start over" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Start over" })).not.toHaveClass("hero-secondary-action")
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

  it("renders overflow titles in a horizontal film strip", async () => {
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
    expect(document.querySelector(".more-movies-strip-row--frames")).not.toBeNull()
    expect(screen.getByText("Fourth (2004)")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Show \d+ more/ })).not.toBeInTheDocument()
  })

  it("renders the System Evidence dashboard", async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole("tab", { name: "System Evidence" }))

    expect(await screen.findByRole("heading", { name: "System Evidence" })).toBeInTheDocument()
    expect(screen.getByText("RAG chat p95")).toBeInTheDocument()
    expect(screen.queryByText("Model Comparison")).not.toBeInTheDocument()
  })

  it("isolates threads when switching local chat sessions", async () => {
    chatConfig.assistantMessage = "Comedy picks for you."
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)

    const genreRow = await screen.findByRole("group", { name: "Genre filters" })
    await user.click(within(genreRow).getByRole("button", { name: "Comedy" }))
    await user.click(screen.getByRole("button", { name: "Send" }))

    const thread = await screen.findByRole("log")
    expect(within(thread).getByText("You selected: Comedy")).toBeInTheDocument()
    expect(within(thread).getByText("Comedy picks for you.")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "New chat" }))
    expect(screen.queryByText("Comedy picks for you.")).not.toBeInTheDocument()

    chatConfig.assistantMessage = "Drama picks for you."
    const newChatGenres = await screen.findByRole("group", { name: "Genre filters" })
    await user.click(within(newChatGenres).getByRole("button", { name: "Drama" }))
    await user.click(screen.getByRole("button", { name: "Send" }))

    const dramaThread = await screen.findByRole("log")
    expect(within(dramaThread).getByText("You selected: Drama")).toBeInTheDocument()
    expect(within(dramaThread).getByText("Drama picks for you.")).toBeInTheDocument()

    const sessionList = document.querySelector(".chat-session-list") as HTMLElement
    await user.click(
      within(sessionList).getByRole("button", { name: "You selected: Comedy" })
    )

    const restoredThread = await screen.findByRole("log")
    expect(within(restoredThread).getByText("You selected: Comedy")).toBeInTheDocument()
    expect(within(restoredThread).getByText("Comedy picks for you.")).toBeInTheDocument()
    expect(screen.queryByText("Drama picks for you.")).not.toBeInTheDocument()
  })

  it("shows dev debug panel when final includes debug payload", async () => {
    chatConfig.debug = {
      resolve_outcome: "ready",
      seed_source: "genre_bootstrap",
      normalized_genres: ["Comedy"],
      ranking_mode: "multi_retriever_fusion",
    }
    vi.stubGlobal("fetch", createFetchMock(chatConfig))

    const user = userEvent.setup()
    render(<App />)
    await sendChat(user, "hi")

    expect(screen.getByText("Debug")).toBeInTheDocument()
    expect(screen.getByText(/genre_bootstrap/)).toBeInTheDocument()
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
      const hero = card.closest(".hero-pick")
      expect(hero).toHaveClass("has-poster")
      expect(hero?.querySelector(".poster-frame--hero .poster-frame__wood")).toBeInTheDocument()
      expect(hero?.querySelector(".poster-frame__mat")).toBeInTheDocument()
    })
  })

  describe("Living Room Shelf shell", () => {
    it("shows the Living Room Shelf brand in the header", () => {
      render(<App />)
      expect(screen.getByText("Living Room Shelf")).toBeInTheDocument()
    })

    it("exposes icon-only send control in the composer", () => {
      render(<App />)
      expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument()
      expect(screen.queryByRole("button", { name: "Attach file" })).not.toBeInTheDocument()
    })

    it("renders assistant sofa avatar after a reply", async () => {
      chatConfig.assistantMessage = "Here are some picks."
      vi.stubGlobal("fetch", createFetchMock(chatConfig))

      const user = userEvent.setup()
      render(<App />)
      await sendChat(user, "hello")

      expect(await screen.findByText("Here are some picks.")).toBeInTheDocument()
      expect(document.querySelector(".assistant-avatar")).toBeInTheDocument()
    })

    it("renders wooden shelf under the more-movies strip", async () => {
      chatConfig.items = Array.from({ length: 4 }, (_, index) => ({
        movie_id: index + 2,
        title: `Shelf Film ${index + 2}`,
        score: 0.7,
      }))
      vi.stubGlobal("fetch", createFetchMock(chatConfig))

      const user = userEvent.setup()
      render(<App />)
      await sendChat(user, "more films")

      expect(
        await screen.findByRole("heading", { name: "More movies you might like" })
      ).toBeInTheDocument()
      expect(document.querySelector(".wood-shelf")).not.toBeInTheDocument()
      expect(
        document.querySelector(".more-movies-strip-row--frames .poster-frame--strip")
      ).toBeInTheDocument()
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
