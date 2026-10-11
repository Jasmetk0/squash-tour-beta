import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type {
  AuthoritativeSimulationPosition,
  AuthoritativeWeekSchedulePreflight
} from '../api/types'
import { CanonicalSimulationBlockerGuide } from './CanonicalSimulationBlockerGuide'

const base: AuthoritativeSimulationPosition = {
  run_id: 'run-a',
  branch_id: 'branch-a',
  current_week: { season_index: 0, week: 5 },
  current_slot_kind: 'match',
  current_slot_id: 'slot-a',
  slot_ordinal: 3,
  unresolved_group_ids: ['g-1'],
  eligible_match_ids: ['g-1'],
  blocked_match_ids: [],
  current_slot_complete: false,
  supported_tournament_complete: false,
  week_ready_for_transition: false,
  transition_blockers: ['pending_authoritative_groups'],
  terminal_sporting_fingerprint: null,
  position_fingerprint: 'a'.repeat(64)
}

const preflight: AuthoritativeWeekSchedulePreflight = {
  schema_version: 'authoritative_week_schedule_preflight.v1',
  run_id: 'run-a',
  branch_id: 'branch-a',
  week: { season_index: 0, week: 5 },
  event_ids: [],
  group_ids: [],
  schedule_required: false,
  schedule_already_adopted: false,
  canonical_preparation: null,
  canonical_preparation_ready: true,
  blockers: [],
  can_propose_schedule: false,
  expected_position_fingerprint: 'b'.repeat(64),
  preflight_fingerprint: 'c'.repeat(64),
  read_only: true
}

function show(
  position: AuthoritativeSimulationPosition | undefined = base,
  schedule: AuthoritativeWeekSchedulePreflight | undefined = preflight,
  available = true,
  scheduleInspectionAvailable = true
) {
  return render(
    <CanonicalSimulationBlockerGuide
      runId="run-a"
      branchId="branch-a"
      available={available}
      position={position}
      schedulePreflight={schedule}
      scheduleInspectionAvailable={scheduleInspectionAvailable}
    />
  )
}

describe('CanonicalSimulationBlockerGuide', () => {
  it('shows scoped authoritative blockers with navigation only to an existing review', () => {
    show()
    const guide = screen.getByRole('region', { name: 'Canonical simulation blocker guide' })
    expect(within(guide).getByText('pending_authoritative_groups')).toBeInTheDocument()
    expect(within(guide).getByRole('link', { name: 'Inspect current matches' }))
      .toHaveAttribute('href', '#canonical-current-slot')
    expect(within(guide).queryByRole('button')).not.toBeInTheDocument()
  })

  it('routes an exact Entry Slot, Ranking-only blocker and Week 61 to their distinct reviews', () => {
    const entry = { ...base, current_slot_kind: 'entry' as const, transition_blockers: ['entry_validation_pending'] }
    const result = show(entry)
    expect(screen.getByRole('link', { name: 'Inspect Entry review' }))
      .toHaveAttribute('href', '#canonical-entry-validation')
    result.rerender(
      <CanonicalSimulationBlockerGuide
        runId="run-a" branchId="branch-a" available position={{
          ...base, current_slot_kind: null, transition_blockers: ['ranking_transition_authority_missing']
        }} schedulePreflight={preflight} scheduleInspectionAvailable
      />
    )
    expect(screen.getByRole('link', { name: 'Inspect Ranking Authority' }))
      .toHaveAttribute('href', '#canonical-ranking-authority')
    const endOfSeason = { ...base, current_week: { season_index: 0, week: 61 }, transition_blockers: ['season_transition_required'] }
    result.rerender(
      <CanonicalSimulationBlockerGuide
        runId="run-a" branchId="branch-a" available position={endOfSeason}
        schedulePreflight={{ ...preflight, week: endOfSeason.current_week }} scheduleInspectionAvailable
      />
    )
    expect(screen.getByRole('link', { name: 'Inspect season preflight' }))
      .toHaveAttribute('href', '#canonical-season-transition')
    expect(screen.queryByRole('link', { name: 'Inspect Week Transition review' }))
      .not.toBeInTheDocument()
  })

  it('does not offer a Ranking preview while other canonical blockers remain', () => {
    show({ ...base, transition_blockers: ['pending_authoritative_groups', 'ranking_transition_authority_missing'] })
    expect(screen.queryByRole('link', { name: 'Inspect Ranking Authority' })).not.toBeInTheDocument()
    expect(screen.getByText(/Resolve the other canonical blockers first/)).toBeInTheDocument()
  })

  it('never routes an unknown blocker or an inconsistent Entry Slot', () => {
    show({
      ...base,
      current_slot_kind: null,
      transition_blockers: ['unrecognized_future_blocker', 'entry_validation_pending']
    })
    expect(screen.getByText('unrecognized_future_blocker')).toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('fails closed when Run, Branch, Week or fingerprint identity is invalid', () => {
    const cases: Array<{
      position: AuthoritativeSimulationPosition
      schedule: AuthoritativeWeekSchedulePreflight
    }> = [
      { position: { ...base, branch_id: 'foreign' }, schedule: preflight },
      { position: base, schedule: { ...preflight, run_id: 'foreign' } },
      { position: base, schedule: { ...preflight, week: { season_index: 0, week: 6 } } },
      { position: { ...base, position_fingerprint: 'invalid' }, schedule: preflight },
      { position: { ...base, current_week: { season_index: 50, week: 1 } }, schedule: preflight }
    ]
    for (const item of cases) {
      const result = show(item.position, item.schedule)
      expect(screen.getByText(/Not verified:/)).toBeInTheDocument()
      expect(screen.queryByRole('link')).not.toBeInTheDocument()
      result.unmount()
    }
  })

  it('surfaces missing Week Schedule and raw preparation blockers without simulating a fix', () => {
    show(undefined, {
      ...preflight,
      schedule_required: true,
      blockers: ['tournament_entry_field_required'],
      canonical_preparation_ready: false
    })
    expect(screen.getByText('tournament_entry_field_required')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Inspect Week Schedule review' }))
      .toHaveAttribute('href', '#canonical-week-schedule')
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('does not advertise a link if the Week Schedule inspection cannot be displayed', () => {
    show(undefined, { ...preflight, schedule_required: true }, true, false)
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('shows unverified when the Branch has no Saved Revision head', () => {
    show(base, preflight, false)
    expect(screen.getByText(/an active writable Branch with a Saved Revision head is required/)).toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('offers Week Transition review only for an explicitly ready, ordinary week', () => {
    show({
      ...base,
      current_slot_kind: null,
      unresolved_group_ids: [],
      transition_blockers: [],
      week_ready_for_transition: true
    })
    expect(screen.getByRole('link', { name: 'Inspect Week Transition review' }))
      .toHaveAttribute('href', '#canonical-week-transition')
  })

  it('does not infer readiness when the engine has no blocker codes but readiness is false', () => {
    show({ ...base, transition_blockers: [], week_ready_for_transition: false })
    expect(screen.getByText(/has not confirmed Week Transition readiness/)).toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })
})
