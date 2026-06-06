// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest"
import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it } from "vitest"
import { MoreMoviesStrip } from "./MoreMoviesStrip"

describe("MoreMoviesStrip", () => {
  afterEach(() => {
    cleanup()
  })

  const items = Array.from({ length: 9 }, (_, index) => ({
    movie_id: index + 2,
    title: `Film ${index + 2} (2001)`,
    score: 0.8,
  }))

  it("shows five tiles and a Show all toggle when more remain", () => {
    render(<MoreMoviesStrip items={items} />)

    expect(screen.getByRole("heading", { name: "More movies you might like" })).toBeInTheDocument()
    expect(screen.getByText("Film 6 (2001)")).toBeInTheDocument()
    expect(screen.queryByText("Film 10 (2001)")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Show all (4)" })).toBeInTheDocument()
  })

  it("expands to the full strip and supports Show fewer", async () => {
    render(<MoreMoviesStrip items={items} />)
    const user = userEvent.setup()

    await user.click(screen.getByRole("button", { name: "Show all (4)" }))
    expect(await screen.findByText("Film 10 (2001)")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Show fewer" })).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Show fewer" }))
    expect(screen.queryByText("Film 10 (2001)")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Show all (4)" })).toBeInTheDocument()
  })
})
