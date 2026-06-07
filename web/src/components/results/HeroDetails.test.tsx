// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest"
import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it } from "vitest"
import { HeroDetails } from "./HeroDetails"

describe("HeroDetails", () => {
  afterEach(() => {
    cleanup()
  })

  it("renders overview, genres, and watch link", () => {
    render(
      <HeroDetails
        label="Iron Man 3 (2013)"
        genres={["Action", "Adventure"]}
        overview="Tony Stark faces a powerful enemy."
        watchUrl="https://www.themoviedb.org/movie/68721"
      />
    )

    expect(screen.getByRole("heading", { name: "Iron Man 3 (2013)" })).toBeInTheDocument()
    expect(screen.getByText("Tony Stark faces a powerful enemy.")).toBeInTheDocument()
    expect(screen.getByText("Action")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /Where to watch/i })).toHaveAttribute(
      "href",
      "https://www.themoviedb.org/movie/68721"
    )
  })

  it("omits overview when missing", () => {
    render(
      <HeroDetails
        label="Mystery Movie (2000)"
        genres={["Drama"]}
        watchUrl="https://www.themoviedb.org/movie/1"
      />
    )

    expect(screen.queryByText(/Tony Stark/)).toBeNull()
    expect(screen.getByText("Drama")).toBeInTheDocument()
  })
})
