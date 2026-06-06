export function buildUserTurnContent(
  message: string,
  genres: string[],
  options?: { hasSessionSeeds?: boolean; hasSessionGenres?: boolean }
): string {
  const trimmed = message.trim()
  if (trimmed) {
    return trimmed
  }
  if (genres.length > 0) {
    return `You selected: ${genres.join(", ")}`
  }
  if (options?.hasSessionSeeds || options?.hasSessionGenres) {
    return "Show more recommendations."
  }
  return ""
}

export function canSendChatTurn(
  message: string,
  genres: string[],
  options?: {
    chatLoading?: boolean
    hasSessionSeeds?: boolean
    hasSessionGenres?: boolean
  }
): boolean {
  if (options?.chatLoading) {
    return false
  }
  return (
    message.trim().length > 0 ||
    genres.length > 0 ||
    Boolean(options?.hasSessionSeeds) ||
    Boolean(options?.hasSessionGenres)
  )
}
