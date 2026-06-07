import type { ChatTurn } from "../types"
import { normalizeChatTurn } from "./chatTurnView"

export type StoredChatSession = {
  id: string
  apiSessionId: string | null
  title: string
  turns: ChatTurn[]
  updatedAt: number
}

const STORAGE_KEY = "movie-reco-chat-sessions"
const ACTIVE_KEY = "movie-reco-chat-active-id"

function readSessions(): StoredChatSession[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as StoredChatSession[]
    return Array.isArray(parsed)
      ? parsed.map((session) => ({
          ...session,
          turns: Array.isArray(session.turns)
            ? session.turns.map((turn) => normalizeChatTurn(turn))
            : [],
        }))
      : []
  } catch {
    return []
  }
}

function writeSessions(sessions: StoredChatSession[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
}

export function loadChatSessions(): StoredChatSession[] {
  return readSessions().sort((a, b) => b.updatedAt - a.updatedAt)
}

export function loadActiveSessionId(): string | null {
  return localStorage.getItem(ACTIVE_KEY)
}

export function saveActiveSessionId(id: string | null): void {
  if (id) {
    localStorage.setItem(ACTIVE_KEY, id)
  } else {
    localStorage.removeItem(ACTIVE_KEY)
  }
}

export function createChatSession(title = "New chat"): StoredChatSession {
  const session: StoredChatSession = {
    id: `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    apiSessionId: null,
    title,
    turns: [],
    updatedAt: Date.now(),
  }
  const sessions = readSessions()
  sessions.unshift(session)
  writeSessions(sessions)
  saveActiveSessionId(session.id)
  return session
}

export function upsertChatSession(session: StoredChatSession): void {
  const sessions = readSessions()
  const index = sessions.findIndex((row) => row.id === session.id)
  const next = { ...session, updatedAt: Date.now() }
  if (index >= 0) {
    sessions[index] = next
  } else {
    sessions.unshift(next)
  }
  writeSessions(sessions)
}

export function deleteChatSession(sessionId: string): StoredChatSession | null {
  const sessions = readSessions().filter((row) => row.id !== sessionId)
  writeSessions(sessions)
  const active = loadActiveSessionId()
  if (active === sessionId) {
    const fallback = sessions[0] ?? null
    saveActiveSessionId(fallback?.id ?? null)
    return fallback
  }
  return sessions.find((row) => row.id === active) ?? sessions[0] ?? null
}

export function deriveSessionTitle(turns: ChatTurn[]): string {
  const firstUser = turns.find((turn) => turn.role === "user")
  if (!firstUser?.content) {
    return "New chat"
  }
  const trimmed = firstUser.content.trim()
  return trimmed.length > 48 ? `${trimmed.slice(0, 45)}…` : trimmed
}
