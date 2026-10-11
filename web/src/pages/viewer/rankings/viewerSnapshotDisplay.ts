import type { RaceSnapshot, RankingSnapshot } from '../../../api/types'

export type ViewerSnapshot = RankingSnapshot | RaceSnapshot

export function latestSnapshot<T extends ViewerSnapshot>(snapshots: T[]): T | null {
  return [...snapshots].sort((a, b) => b.snapshot_sequence - a.snapshot_sequence)[0] ?? null
}
