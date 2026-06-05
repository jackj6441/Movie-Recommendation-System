// @vitest-environment jsdom

import { describe, expect, it, vi } from "vitest"
import { scrollLatestAssistantBubble } from "./scrollLatestAssistant"

describe("scrollLatestAssistantBubble", () => {
  it("scrolls the last assistant bubble in the container", () => {
    const root = document.createElement("div")
    root.innerHTML = `
      <article class="chat-bubble chat-bubble--assistant">first</article>
      <article class="chat-bubble chat-bubble--assistant">latest</article>
    `
    const scrollIntoView = vi.fn()
    const latest = root.querySelectorAll(".chat-bubble--assistant")[1] as HTMLElement
    latest.scrollIntoView = scrollIntoView

    scrollLatestAssistantBubble(root)

    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "start" })
  })
})
