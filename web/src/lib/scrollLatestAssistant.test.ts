// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { scrollLatestAssistantBubble } from "./scrollLatestAssistant"

describe("scrollLatestAssistantBubble", () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
      callback(0)
      return 0
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it("scrolls the last assistant bubble in the container", () => {
    const root = document.createElement("div")
    root.innerHTML = `
      <article class="chat-bubble chat-bubble--assistant">first</article>
      <article class="chat-bubble chat-bubble--assistant">latest</article>
    `
    const scrollIntoView = vi.fn()
    const latest = root.querySelectorAll(".chat-bubble--assistant")[1] as HTMLElement
    latest.scrollIntoView = scrollIntoView
    Object.defineProperty(latest, "getBoundingClientRect", {
      value: () => ({ top: 200, left: 0, width: 0, height: 0, right: 0, bottom: 0 }),
    })

    scrollLatestAssistantBubble(root)
    vi.runAllTimers()

    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "start" })
  })
})
