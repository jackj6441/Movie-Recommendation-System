export type SseEvent = {
  event: string
  data: unknown
}

export function parseSsePayload(body: string): SseEvent[] {
  const events: SseEvent[] = []
  for (const block of body.split("\n\n")) {
    const trimmed = block.trim()
    if (!trimmed) continue
    let eventName = "message"
    let dataLine: string | null = null
    for (const line of trimmed.split("\n")) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim()
      } else if (line.startsWith("data:")) {
        dataLine = line.slice(5).trim()
      }
    }
    if (dataLine !== null) {
      events.push({ event: eventName, data: JSON.parse(dataLine) })
    }
  }
  return events
}
