import { MAX_SEEDS } from "../config"

export type SeedAddState = {
  isInSeeds: boolean
  seedSetFull: boolean
  canAdd: boolean
}

export function seedAddState(
  movieId: number,
  seedMovieIds: number[],
  maxSeeds = MAX_SEEDS
): SeedAddState {
  const isInSeeds = seedMovieIds.includes(movieId)
  const seedSetFull = seedMovieIds.length >= maxSeeds
  return {
    isInSeeds,
    seedSetFull,
    canAdd: !isInSeeds && !seedSetFull,
  }
}
