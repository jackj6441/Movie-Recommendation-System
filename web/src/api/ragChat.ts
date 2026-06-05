import { apiBase } from "../config"
import { parseSsePayload } from "../lib/parseSse"
import type { RagChatFinal, RagChatStreamResult } from "../types"

export type RagChatRequest = {
  session_id: string | null
  message: string
  genres: string[]
  shuffle?: boolean
}

export async function postRagChat(request: RagChatRequest): Promise<RagChatStreamResult> {
  const res = await fetch(`${apiBase}/rag/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: request.session_id,
      message: request.message,
      genres: request.genres,
      shuffle: request.shuffle ?? false,
    }),
  })
  if (!res.ok) {
    throw new Error(`Chat request failed: ${res.status}`)
  }
  const body = await res.text()
  const events = parseSsePayload(body)
  const tokens = events
    .filter((entry) => entry.event === "token")
    .map((entry) => (entry.data as { delta: string }).delta)
    .join("")
  const finalEntry = events.find((entry) => entry.event === "final")
  if (!finalEntry) {
    throw new Error("Chat response missing final event")
  }
  const final = finalEntry.data as RagChatFinal
  return {
    tokens,
    final,
    assistantMessage: final.assistant_message || tokens,
  }
}
