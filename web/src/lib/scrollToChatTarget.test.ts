// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { scrollToChatTarget } from "./scrollToChatTarget"

function flushScrollTimers(): void {
  vi.runAllTimers()
}

describe("scrollToChatTarget", () => {
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

  it("retries until the target appears in the DOM", () => {
    const root = document.createElement("div")
    const scrollIntoView = vi.fn()

    scrollToChatTarget(".chat-bubble--assistant", root, {
      retryDelayMs: 50,
      maxAttempts: 8,
    })

    vi.advanceTimersByTime(50)
    expect(scrollIntoView).not.toHaveBeenCalled()

    const bubble = document.createElement("article")
    bubble.className = "chat-bubble chat-bubble--assistant"
    bubble.scrollIntoView = scrollIntoView
    Object.defineProperty(bubble, "getBoundingClientRect", {
      value: () => ({ top: 120, left: 0, width: 0, height: 0, right: 0, bottom: 0 }),
    })
    root.appendChild(bubble)

    flushScrollTimers()

    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "start" })
  })

  it("retries when scroll position does not change", () => {
    const root = document.createElement("div")
    const bubble = document.createElement("article")
    bubble.className = "chat-bubble chat-bubble--assistant"
    const scrollIntoView = vi.fn()
    bubble.scrollIntoView = scrollIntoView
    Object.defineProperty(bubble, "getBoundingClientRect", {
      value: () => ({ top: 0, left: 0, width: 0, height: 0, right: 0, bottom: 0 }),
    })
    root.appendChild(bubble)

    scrollToChatTarget(".chat-bubble--assistant", root, {
      retryDelayMs: 40,
      maxAttempts: 3,
    })

    flushScrollTimers()

    expect(scrollIntoView.mock.calls.length).toBeGreaterThanOrEqual(2)
  })
})
