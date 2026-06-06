// @vitest-environment jsdom

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { stubLocalStorage } from "../test/localStorageMock"
import {
  createChatSession,
  deleteChatSession,
  loadChatSessions,
  upsertChatSession,
} from "./chatSessionStore"

describe("chatSessionStore", () => {
  beforeEach(() => {
    stubLocalStorage()
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("creates and lists sessions", () => {
    const session = createChatSession("Comedy night")
    const sessions = loadChatSessions()
    expect(sessions[0]?.id).toBe(session.id)
    expect(sessions[0]?.title).toBe("Comedy night")
  })

  it("deletes a session and returns fallback", () => {
    const first = createChatSession("First")
    const second = createChatSession("Second")
    upsertChatSession({ ...second, updatedAt: Date.now() + 1 })
    const fallback = deleteChatSession(first.id)
    expect(fallback?.id).toBe(second.id)
    expect(loadChatSessions()).toHaveLength(1)
  })
})
