import { describe, expect, it } from "vitest"
import { MAX_SEEDS } from "../config"
import { seedAddState, seedSetFullTitle } from "./seedAdd"

describe("seedAddState", () => {
  it("allows add when movie is new and under the cap", () => {
    expect(seedAddState(10, [1, 2])).toEqual({
      isInSeeds: false,
      seedSetFull: false,
      canAdd: true,
    })
  })

  it("blocks add when movie is already in seeds", () => {
    expect(seedAddState(2, [1, 2, 3])).toEqual({
      isInSeeds: true,
      seedSetFull: false,
      canAdd: false,
    })
  })

  it("blocks add when the seed set is full", () => {
    const fullSet = Array.from({ length: MAX_SEEDS }, (_, index) => index + 1)
    expect(seedAddState(99, fullSet)).toEqual({
      isInSeeds: false,
      seedSetFull: true,
      canAdd: false,
    })
  })

  it("formats the seed-set-full tooltip from the cap", () => {
    expect(seedSetFullTitle()).toBe(`Seed set full (max ${MAX_SEEDS})`)
  })
})
