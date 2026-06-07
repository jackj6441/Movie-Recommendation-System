// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest"
import { cleanup, render } from "@testing-library/react"
import { afterEach, describe, expect, it } from "vitest"
import { SidebarSceneDecor } from "./SidebarSceneDecor"

describe("SidebarSceneDecor", () => {
  afterEach(() => {
    cleanup()
  })

  it("renders lamp vignette for left wing", () => {
    const { container } = render(<SidebarSceneDecor variant="lamp" />)
    const root = container.querySelector(".sidebar-scene-decor--lamp")
    expect(root).toBeInTheDocument()
    expect(root).toHaveAttribute("aria-hidden", "true")
    expect(container.querySelector('img[src="/assets/living-room/scene-lamp-left.png"]')).toBeInTheDocument()
  })

  it("renders console vignette for right wing", () => {
    const { container } = render(<SidebarSceneDecor variant="console" />)
    expect(container.querySelector(".sidebar-scene-decor--console")).toBeInTheDocument()
    expect(container.querySelector('img[src="/assets/living-room/scene-console-right.png"]')).toBeInTheDocument()
  })
})
