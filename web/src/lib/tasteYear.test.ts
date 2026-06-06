// @vitest-environment jsdom
import { describe, expect, it } from "vitest"
import {
  DEFAULT_RECENCY_MIN,
  YEAR_TRACK_MAX,
  contextToSlider,
  formatYearSummary,
  isAnyYear,
  sliderMatchesContext,
  sliderValuesToApi,
} from "./tasteYear"
import type { RagChatContext } from "../types"

describe("tasteYear", () => {
  const base: RagChatContext = {
    seeds: [],
    genres: ["Comedy"],
    year_min: DEFAULT_RECENCY_MIN,
    year_max: null,
    recency_opt_out: false,
  }

  it("detects any year from recency opt out", () => {
    expect(
      isAnyYear({
        ...base,
        year_min: null,
        year_max: null,
        recency_opt_out: true,
      })
    ).toBe(true)
  })

  it("maps default recency to slider thumbs", () => {
    expect(contextToSlider(base)).toEqual({
      min: DEFAULT_RECENCY_MIN,
      max: YEAR_TRACK_MAX,
      anyYear: false,
    })
  })

  it("formats collapsed year summary", () => {
    expect(formatYearSummary(base)).toBe(`2005–${YEAR_TRACK_MAX}`)
    expect(
      formatYearSummary({
        ...base,
        year_min: null,
        year_max: null,
        recency_opt_out: true,
      })
    ).toBe("Any year")
  })

  it("detects draft slider state that differs from committed context", () => {
    expect(
      sliderMatchesContext(
        { min: 2019, max: YEAR_TRACK_MAX, anyYear: false },
        base
      )
    ).toBe(false)
    expect(sliderMatchesContext(contextToSlider(base), base)).toBe(true)
  })

  it("omits year_max when slider is at track max", () => {
    expect(sliderValuesToApi(2005, YEAR_TRACK_MAX)).toEqual({
      year_min: 2005,
      year_max: null,
    })
    expect(sliderValuesToApi(1990, 2004)).toEqual({
      year_min: 1990,
      year_max: 2004,
    })
  })
})
