import type { RagChatContext } from "../types"

export function formatTasteSummary(context: RagChatContext): string {
  const parts: string[] = []
  if (context.seeds.length > 0) {
    const count = context.seeds.length
    parts.push(`${count} ${count === 1 ? "movie" : "movies"}`)
  }
  if (context.genres.length > 0) {
    parts.push(context.genres.join(", "))
  }
  if (context.year_min != null || context.year_max != null) {
    if (context.year_min != null && context.year_max != null) {
      parts.push(`years ${context.year_min}–${context.year_max}`)
    } else if (context.year_min != null) {
      parts.push(`${context.year_min}+`)
    } else if (context.year_max != null) {
      parts.push(`before ${context.year_max}`)
    }
  }
  if (parts.length === 0) {
    return "Current taste"
  }
  return `Current taste · ${parts.join(", ")}`
}
