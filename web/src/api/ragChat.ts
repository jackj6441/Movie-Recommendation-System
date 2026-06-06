import { apiBase } from "../config"
import { parseSsePayload } from "../lib/parseSse"
import type { RagChatFinal, RagChatStreamResult } from "../types"

export type RagChatRequest = {
  session_id: string | null
  message: string
  genres: string[]
  seed_movie_ids?: number[]
  seed_update_mode?: "append" | "replace"
  reset_context?: boolean
  clear_year_bounds?: boolean
  year_min?: number | null
  year_max?: number | null
  disambiguation_genre?: string
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
      seed_movie_ids: request.seed_movie_ids,
      seed_update_mode: request.seed_update_mode,
      reset_context: request.reset_context ?? false,
      clear_year_bounds: request.clear_year_bounds ?? false,
      year_min: request.year_min ?? null,
      year_max: request.year_max ?? null,
      disambiguation_genre: request.disambiguation_genre,
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
