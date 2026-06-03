export function formatTitle(raw: string): string {
  return raw.replace(/^(.*),\s+(The|A|An)\s+(\(\d{4}\))$/, "$2 $1 $3")
}

export function formatMetric(value: number): string {
  return value.toFixed(3)
}

export function formatLatency(value: number): string {
  return `${value.toFixed(1)} ms`
}

export function sortGenres(names: string[], priority: readonly string[]): string[] {
  const set = new Set(names)
  const ordered: string[] = []
  priority.forEach((genre) => {
    if (set.has(genre)) {
      ordered.push(genre)
      set.delete(genre)
    }
  })
  return [...ordered, ...[...set].sort()]
}
