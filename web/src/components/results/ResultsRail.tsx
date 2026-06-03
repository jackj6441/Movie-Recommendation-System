import type { MovieSuggestion } from "../../types"
import type { TimeRangeKey } from "../../config"
import { ContextRail } from "../layout/ContextRail"
import { ResultsFilters } from "./ResultsFilters"

type ResultsRailProps = {
  seeds: MovieSuggestion[]
  genres: string[]
  resultTopics: string[]
  timeRange: TimeRangeKey
  disabled: boolean
  onToggleTopic: (genre: string) => void
  onChangeTimeRange: (key: TimeRangeKey) => void
  onResetFilters: () => void
}

export function ResultsRail({ seeds, ...filters }: ResultsRailProps) {
  return (
    <ContextRail seeds={seeds}>
      <ResultsFilters {...filters} />
    </ContextRail>
  )
}
