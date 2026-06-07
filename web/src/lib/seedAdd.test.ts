import { describe, expect, it } from "vitest"
import { seedAddState } from "./seedAdd"

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
    expect(seedAddState(99, [1, 2, 3, 4, 5])).toEqual({
      isInSeeds: false,
      seedSetFull: true,
      canAdd: false,
    })
  })
})
