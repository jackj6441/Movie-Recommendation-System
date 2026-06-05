import { describe, expect, it } from "vitest"
import { buildUserTurnContent, canSendChatTurn } from "./chatUserTurn"

describe("chatUserTurn", () => {
  it("allows send with genre chips only", () => {
    expect(canSendChatTurn("", ["Comedy"])).toBe(true)
    expect(buildUserTurnContent("", ["Comedy"])).toBe("You selected: Comedy")
  })

  it("allows send with session seeds and empty composer", () => {
    expect(canSendChatTurn("", [], { hasSessionSeeds: true })).toBe(true)
    expect(buildUserTurnContent("", [], { hasSessionSeeds: true })).toBe(
      "Show more recommendations."
    )
  })

  it("blocks send while loading", () => {
    expect(canSendChatTurn("hi", ["Comedy"], { chatLoading: true })).toBe(false)
  })

  it("prefers typed message over genre summary", () => {
    expect(buildUserTurnContent("Toy Story", ["Comedy"])).toBe("Toy Story")
  })
})
