// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest"
import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"
import { SeedPosterTile } from "./SeedPosterTile"

describe("SeedPosterTile", () => {
  afterEach(() => {
    cleanup()
  })

  it("renders a strip frame with poster art", () => {
    const { container } = render(
      <SeedPosterTile
        seed={{
          movie_id: 1,
          title: "Toy Story (1995)",
          poster_thumb_url: "https://image.tmdb.org/t/p/w185/poster.jpg",
        }}
        onRemove={vi.fn()}
      />
    )

    expect(container.querySelector(".taste-seed-tile__frame.poster-frame--strip")).toBeInTheDocument()
    expect(container.querySelector('img[src="https://image.tmdb.org/t/p/w185/poster.jpg"]')).toBeInTheDocument()
  })

  it("calls onRemove when clicked", async () => {
    const onRemove = vi.fn()
    const user = userEvent.setup()

    render(
      <SeedPosterTile
        seed={{ movie_id: 1, title: "Toy Story (1995)" }}
        onRemove={onRemove}
      />
    )

    await user.click(
      screen.getByRole("button", { name: "Remove Toy Story (1995) from starting movies" })
    )
    expect(onRemove).toHaveBeenCalledOnce()
  })
})
