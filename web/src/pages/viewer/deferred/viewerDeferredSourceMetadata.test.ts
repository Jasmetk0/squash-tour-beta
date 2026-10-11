import { describe, expect, it } from 'vitest'

import type { EventRecord, FinalsSummaryResponse, RaceSnapshot, RankingSnapshot, RunStatusSummary } from '../../../api/types'
import {
  buildDeferredSourceMetadata,
  hasAnyDeferredSourceMetadata,
  hasAvailableFinals,
  resolveFinalsAvailability
} from './viewerDeferredSourceMetadata'

function buildStatus(overrides: Partial<RunStatusSummary> = {}): RunStatusSummary {
  return {
    run_id: 'source run',
    season: 2034,
    seed: 11,
    progress: { next_event_index: 0, total_events: 0, completed_event_count: 0 },
    finals: { qualification_available: false, result_available: false },
    rollover: null,
    source: { source_type: 'fresh_seed', parent_run_id: null },
    lineage: { child_run_count: 0 },
    history_counts: { events: 0, ranking_snapshots: 0, race_snapshots: 0 },
    ...overrides
  }
}

const events: EventRecord[] = [
  { event_id: 'EVT-1', event_sequence: 1, season: 2034, week: 1, template_id: 'TPL-1', tournament_result: {} },
  { event_id: 'EVT-9', event_sequence: 9, season: 2034, week: 9, template_id: 'TPL-9', tournament_result: {} },
  { event_id: 'EVT-3', event_sequence: 3, season: 2034, week: 3, template_id: 'TPL-3', tournament_result: {} }
]

const rankingSnapshots: RankingSnapshot[] = [
  { snapshot_sequence: 2, snapshot_kind: 'ranking', source_event_id: 'EVT-2', payload: {} },
  { snapshot_sequence: 8, snapshot_kind: 'ranking', source_event_id: 'EVT-8', payload: {} }
]

const raceSnapshots: RaceSnapshot[] = [
  { snapshot_sequence: 4, snapshot_kind: 'race', source_event_id: 'EVT-4', payload: {} },
  { snapshot_sequence: 6, snapshot_kind: 'race', source_event_id: 'EVT-6', payload: {} }
]

describe('viewerDeferredSourceMetadata', () => {
  it('builds counts and latest source references from available source arrays', () => {
    const metadata = buildDeferredSourceMetadata({
      events,
      rankingSnapshots,
      raceSnapshots,
      status: buildStatus({ history_counts: { events: 99, ranking_snapshots: 99, race_snapshots: 99 } }),
      finals: { run_id: 'source run', season: 2034, qualification: null, result: null }
    })

    expect(metadata.eventCount).toBe(3)
    expect(metadata.rankingSnapshotCount).toBe(2)
    expect(metadata.raceSnapshotCount).toBe(2)
    expect(metadata.latestPersistedEvent?.event_id).toBe('EVT-9')
    expect(metadata.latestRankingSnapshot?.snapshot_sequence).toBe(8)
    expect(metadata.latestRaceSnapshot?.snapshot_sequence).toBe(6)
    expect(metadata.finalsAvailability).toBe('Finals summary not available yet')
    expect(metadata.hasFinalsAvailability).toBe(false)
  })

  it('falls back to status history counts when source arrays are unavailable', () => {
    const metadata = buildDeferredSourceMetadata({
      events: undefined,
      rankingSnapshots: undefined,
      raceSnapshots: undefined,
      status: buildStatus({ history_counts: { events: 5, ranking_snapshots: 3, race_snapshots: 2 } }),
      finals: undefined
    })

    expect(metadata.eventCount).toBe(5)
    expect(metadata.rankingSnapshotCount).toBe(3)
    expect(metadata.raceSnapshotCount).toBe(2)
    expect(metadata.latestPersistedEvent).toBeNull()
    expect(metadata.latestRankingSnapshot).toBeNull()
    expect(metadata.latestRaceSnapshot).toBeNull()
  })

  it('uses finals summary before status flags', () => {
    const finals: FinalsSummaryResponse = {
      run_id: 'source run',
      season: 2034,
      qualification: null,
      result: {
        run_id: 'source run',
        season: 2034,
        event_id: 'FINALS',
        source_as_of_season: 2034,
        source_as_of_week: 52,
        result: {}
      }
    }

    expect(resolveFinalsAvailability(finals, buildStatus({ finals: { qualification_available: false, result_available: false } }))).toBe('Finals result available')
  })

  it('preserves status-based finals availability fallback strings', () => {
    expect(resolveFinalsAvailability(undefined, buildStatus({ finals: { qualification_available: false, result_available: true } }))).toBe('Finals result available')
    expect(resolveFinalsAvailability(undefined, buildStatus({ finals: { qualification_available: true, result_available: false } }))).toBe('Finals qualification available')
    expect(resolveFinalsAvailability(undefined, buildStatus())).toBe('Finals summary not available yet')
    expect(resolveFinalsAvailability(undefined, undefined)).toBe('Finals summary not available yet')
    expect(resolveFinalsAvailability({ run_id: 'source run', season: 2034, qualification: null, result: null }, undefined)).toBe('Finals summary not available yet')
    expect(hasAvailableFinals('Loading or unavailable')).toBe(false)
  })

  it('preserves source metadata availability checks with optional ordered calendar count', () => {
    const emptyMetadata = buildDeferredSourceMetadata({ events: [], rankingSnapshots: [], raceSnapshots: [], status: undefined, finals: undefined })
    const finalsMetadata = buildDeferredSourceMetadata({
      events: [],
      rankingSnapshots: [],
      raceSnapshots: [],
      status: buildStatus({ finals: { qualification_available: true, result_available: false } }),
      finals: undefined
    })

    expect(hasAnyDeferredSourceMetadata(emptyMetadata)).toBe(false)
    expect(hasAnyDeferredSourceMetadata(emptyMetadata, 1)).toBe(true)
    expect(hasAnyDeferredSourceMetadata(finalsMetadata)).toBe(true)
  })
})
