import type { RagChatContext } from "../types"

export const YEAR_TRACK_MIN = 1950
export const YEAR_TRACK_MAX = 2025
export const DEFAULT_RECENCY_MIN = 2005

export type SliderYearState = {
  min: number
  max: number
  anyYear: boolean
}

export function isAnyYear(context: RagChatContext): boolean {
  return Boolean(
    context.recency_opt_out && context.year_min == null && context.year_max == null
  )
}

export function contextToSlider(context: RagChatContext): SliderYearState {
  if (isAnyYear(context)) {
    return {
      min: DEFAULT_RECENCY_MIN,
      max: YEAR_TRACK_MAX,
      anyYear: true,
    }
  }
  return {
    min: context.year_min ?? DEFAULT_RECENCY_MIN,
    max: context.year_max ?? YEAR_TRACK_MAX,
    anyYear: false,
  }
}

export function formatYearSummary(context: RagChatContext): string {
  if (isAnyYear(context)) {
    return "Any year"
  }
  return formatYearRangeLabel(context.year_min ?? DEFAULT_RECENCY_MIN, context.year_max)
}

export function formatYearRangeLabel(
  yearMin: number,
  yearMax: number | null
): string {
  if (yearMax == null || yearMax >= YEAR_TRACK_MAX) {
    return `${yearMin}–${YEAR_TRACK_MAX}`
  }
  return `${yearMin}–${yearMax}`
}

export function sliderMatchesContext(
  preview: SliderYearState,
  context: RagChatContext
): boolean {
  const committed = contextToSlider(context)
  if (committed.anyYear !== preview.anyYear) {
    return false
  }
  if (committed.anyYear) {
    return true
  }
  return committed.min === preview.min && committed.max === preview.max
}

/** Map slider thumbs to API bounds; open-ended max omits year_max. */
export function sliderValuesToApi(
  min: number,
  max: number
): { year_min: number; year_max: number | null } {
  return {
    year_min: min,
    year_max: max >= YEAR_TRACK_MAX ? null : max,
  }
}
