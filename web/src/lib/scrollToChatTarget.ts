export type ScrollToChatTargetOptions = {
  behavior?: ScrollBehavior
  block?: ScrollLogicalPosition
  maxAttempts?: number
  retryDelayMs?: number
}

const DEFAULT_OPTIONS: Required<ScrollToChatTargetOptions> = {
  behavior: "smooth",
  block: "start",
  maxAttempts: 8,
  retryDelayMs: 80,
}

/** Scroll a chat target into view with retries until layout stabilizes. */
export function scrollToChatTarget(
  selector: string,
  root: ParentNode = document,
  options: ScrollToChatTargetOptions = {}
): void {
  const resolved = { ...DEFAULT_OPTIONS, ...options }
  let attempts = 0

  const tryScroll = () => {
    const nodes = root.querySelectorAll(selector)
    const target = nodes[nodes.length - 1] as HTMLElement | undefined
    if (!target) {
      if (attempts < resolved.maxAttempts) {
        attempts += 1
        window.setTimeout(tryScroll, resolved.retryDelayMs)
      }
      return
    }

    if (typeof target.scrollIntoView !== "function") {
      return
    }

    const before = target.getBoundingClientRect().top
    target.scrollIntoView({ behavior: resolved.behavior, block: resolved.block })
    const after = target.getBoundingClientRect().top

    if (attempts < resolved.maxAttempts && Math.abs(after - before) < 1) {
      attempts += 1
      window.setTimeout(tryScroll, resolved.retryDelayMs)
    }
  }

  requestAnimationFrame(() => {
    requestAnimationFrame(tryScroll)
  })
}

export function scrollLatestAssistantBubble(root: ParentNode = document): void {
  scrollToChatTarget(".chat-bubble--assistant", root)
}

export function scrollToTurn(turnId: string, root: ParentNode = document): void {
  scrollToChatTarget(`[data-turn-id="${turnId}"]`, root)
}
