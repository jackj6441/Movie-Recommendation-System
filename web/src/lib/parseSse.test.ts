import { describe, expect, it } from "vitest"
import { parseSsePayload } from "./parseSse"

describe("parseSsePayload", () => {
  it("parses token and final events", () => {
    const body =
      'event: token\ndata: {"delta":"Hi"}\n\n' +
      'event: final\ndata: {"session_id":"s1","needs_clarification":false}\n\n'
    const events = parseSsePayload(body)
    expect(events).toHaveLength(2)
    expect(events[0]).toEqual({ event: "token", data: { delta: "Hi" } })
    expect(events[1].event).toBe("final")
  })
})
