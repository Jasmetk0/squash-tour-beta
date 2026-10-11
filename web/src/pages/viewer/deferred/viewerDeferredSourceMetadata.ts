import type { EventRecord, FinalsSummaryResponse, RaceSnapshot, RankingSnapshot, RunStatusSummary } from '../../../api/types'
import { latestSnapshot } from '../rankings/viewerSnapshotDisplay'
import { formatFinalsAvailability, selectLatestPersistedEvent } from '../tour/viewerTourDisplay'

export type DeferredSourceMetadata = {
  eventCount: number | null
  rankingSnapshotCount: number | null
  raceSnapshotCount: number | null
  latestPersistedEvent: EventRecord | null
  latestRankingSnapshot: RankingSnapshot | null
  latestRaceSnapshot: RaceSnapshot | null
  finalsAvailability: string
  hasFinalsAvailability: boolean
}

export function resolveFinalsAvailability(finals: FinalsSummaryResponse | undefined, status: RunStatusSummary | undefined): string {
  if (finals) return formatFinalsAvailability(finals)
  if (status?.finals.result_available) return 'Finals result available'
  if (status?.finals.qualification_available) return 'Finals qualification available'
  return 'Finals summary not available yet'
}

export function hasAvailableFinals(finalsAvailability: string): boolean {
  return finalsAvailability !== 'Finals summary not available yet' && finalsAvailability !== 'Loading or unavailable'
}

export function buildDeferredSourceMetadata(args: {
  events: EventRecord[] | undefined
  rankingSnapshots: RankingSnapshot[] | undefined
  raceSnapshots: RaceSnapshot[] | undefined
  status: RunStatusSummary | undefined
  finals: FinalsSummaryResponse | undefined
  eventCount?: number | null
}): DeferredSourceMetadata {
  const events = args.events ?? []
  const rankingSnapshots = args.rankingSnapshots ?? []
  const raceSnapshots = args.raceSnapshots ?? []
  const eventCount = args.eventCount ?? args.events?.length ?? args.status?.history_counts.events ?? null
  const rankingSnapshotCount = args.rankingSnapshots?.length ?? args.status?.history_counts.ranking_snapshots ?? null
  const raceSnapshotCount = args.raceSnapshots?.length ?? args.status?.history_counts.race_snapshots ?? null
  const finalsAvailability = resolveFinalsAvailability(args.finals, args.status)

  return {
    eventCount,
    rankingSnapshotCount,
    raceSnapshotCount,
    latestPersistedEvent: selectLatestPersistedEvent(events),
    latestRankingSnapshot: latestSnapshot(rankingSnapshots),
    latestRaceSnapshot: latestSnapshot(raceSnapshots),
    finalsAvailability,
    hasFinalsAvailability: hasAvailableFinals(finalsAvailability)
  }
}

export function hasAnyDeferredSourceMetadata(metadata: DeferredSourceMetadata, orderedEventCount?: number | null): boolean {
  return (metadata.eventCount ?? 0) > 0 || (orderedEventCount ?? 0) > 0 || (metadata.rankingSnapshotCount ?? 0) > 0 || (metadata.raceSnapshotCount ?? 0) > 0 || metadata.hasFinalsAvailability
}
