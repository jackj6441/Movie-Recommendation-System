// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest"
import { cleanup, render, screen } from "@testing-library/react"
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

  it("renders all strip tiles in a horizontal scroller without a show-more toggle", () => {
    const { container } = render(<MoreMoviesStrip items={items} />)

    expect(screen.getByRole("heading", { name: "More movies you might like" })).toBeInTheDocument()
    expect(screen.getByText("Film 6 (2001)")).toBeInTheDocument()
    expect(screen.getByText("Film 10 (2001)")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Show \d+ more/ })).not.toBeInTheDocument()
    expect(container.querySelector(".wood-shelf")).not.toBeInTheDocument()
    expect(container.querySelector(".more-movies-strip-scroller.is-scrollable")).toBeInTheDocument()
    expect(container.querySelectorAll(".poster-frame--strip").length).toBe(9)
  })

  it("does not mark the scroller scrollable when only a few items fit", () => {
    const { container } = render(<MoreMoviesStrip items={items.slice(0, 3)} />)

    expect(container.querySelector(".more-movies-strip-scroller.is-scrollable")).not.toBeInTheDocument()
    expect(container.querySelectorAll(".poster-frame--strip").length).toBe(3)
  })
})
