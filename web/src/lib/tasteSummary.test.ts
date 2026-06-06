import { describe, expect, it } from "vitest"
import { formatTasteSummary } from "./tasteSummary"

describe("formatTasteSummary", () => {
  it("summarizes seeds and genres for compact rail", () => {
    expect(
      formatTasteSummary({
        seeds: [{ movie_id: 1, title: "Toy Story (1995)" }],
        genres: ["Comedy"],
        year_min: null,
        year_max: null,
      })
    ).toBe("Current taste · 1 movie, Comedy")
  })
})
