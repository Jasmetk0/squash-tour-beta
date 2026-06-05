import { describe, expect, it } from 'vitest'

import {
  makeRunStatusSummary,
  makeSeasonStateResponse,
} from './viewerDeferredFixtures'

describe('viewerDeferredFixtures', () => {
  it('preserves progress defaults with a partial progress override', () => {
    const summary = makeRunStatusSummary({
      progress: { completed_event_count: 9 },
    })

    expect(summary.progress.next_event_index).toBe(0)
    expect(summary.progress.total_events).toBe(61)
    expect(summary.progress.completed_event_count).toBe(9)
  })

  it('preserves finals defaults with a partial finals override', () => {
    const summary = makeRunStatusSummary({
      finals: { qualification_available: true },
    })

    expect(summary.finals.qualification_available).toBe(true)
    expect(summary.finals.result_available).toBe(false)
  })

  it('preserves history count defaults with a partial history count override', () => {
    const summary = makeRunStatusSummary({
      history_counts: { events: 10 },
    })

    expect(summary.history_counts.events).toBe(10)
    expect(summary.history_counts.ranking_snapshots).toBe(2)
    expect(summary.history_counts.race_snapshots).toBe(1)
  })

  it('keeps top-level run status overrides working', () => {
    const summary = makeRunStatusSummary({ run_id: 'custom run', season: 2040 })

    expect(summary.run_id).toBe('custom run')
    expect(summary.season).toBe(2040)
  })

  it('preserves season state nested defaults with partial nested overrides', () => {
    const state = makeSeasonStateResponse({
      run: { total_events: 77 },
      season_state: { next_event_index: 3 },
    })

    expect(state.run.run_id).toBe('run alpha')
    expect(state.run.total_events).toBe(77)
    expect(state.season_state.season).toBe(2034)
    expect(state.season_state.next_event_index).toBe(3)
  })
})
