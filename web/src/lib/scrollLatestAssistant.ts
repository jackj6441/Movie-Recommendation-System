/** Scroll the newest assistant bubble into view after a chat turn completes. */
export function scrollLatestAssistantBubble(root: ParentNode = document): void {
  const bubbles = root.querySelectorAll(".chat-bubble--assistant")
  const latest = bubbles[bubbles.length - 1]
  latest?.scrollIntoView({ behavior: "smooth", block: "start" })
}
