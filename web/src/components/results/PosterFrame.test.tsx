// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest"
import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"
import { PosterFrame } from "./PosterFrame"

describe("PosterFrame", () => {
  afterEach(() => {
    cleanup()
  })

  it("renders hero wood and mat layers", () => {
    const { container } = render(
      <PosterFrame variant="hero">
        <img className="poster-frame__art" src="/test.jpg" alt="" />
      </PosterFrame>
    )

    expect(container.querySelector(".poster-frame--hero")).toBeInTheDocument()
    expect(container.querySelector(".poster-frame__wood")).toBeInTheDocument()
    expect(container.querySelector(".poster-frame__mat")).toBeInTheDocument()
  })

  it("supports interactive strip frames with accessible labels", async () => {
    const onClick = vi.fn()
    const user = userEvent.setup()

    render(
      <PosterFrame
        variant="strip"
        interactive
        ariaLabel="Add Example Movie to starting movies"
        onClick={onClick}
      >
        <div className="poster-frame__fallback" />
      </PosterFrame>
    )

    await user.click(
      screen.getByRole("button", { name: "Add Example Movie to starting movies" })
    )
    expect(onClick).toHaveBeenCalledOnce()
  })
})
