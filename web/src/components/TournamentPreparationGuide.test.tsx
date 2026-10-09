import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type {
  AuthoritativeWeekSchedulePreflight,
  CanonicalTournamentPreparationState
} from '../api/types'
import { TournamentPreparationGuide } from './TournamentPreparationGuide'

const tournament = (eventId: string): CanonicalTournamentPreparationState => ({
  schema_version: 'canonical_tournament_preparation_state.v1',
  run_id: 'run/a',
  branch_id: 'branch #1',
  event_id: eventId,
  phase: 'draw_ready',
  next_required_action: 'none',
  blockers: [],
  ready_for_match_schedule: true,
  effective_draw_fingerprint: 'a'.repeat(64),
  authority_source: 'run_owned_db_authorities.v1'
})

const preflight = (): AuthoritativeWeekSchedulePreflight => ({
  schema_version: 'authoritative_week_schedule_preflight.v1',
  run_id: 'run/a',
  branch_id: 'branch #1',
  week: { season_index: 0, week: 1 },
  event_ids: ['event/α', 'event-b'],
  group_ids: [],
  schedule_required: true,
  schedule_already_adopted: false,
  canonical_preparation: {
    schema_version: 'canonical_week_schedule_preparation_state.v1',
    run_id: 'run/a',
    branch_id: 'branch #1',
    event_ids: ['event/α', 'event-b'],
    tournaments: [
      tournament('event/α'),
      {
        ...tournament('event-b'),
        phase: 'entry_field_required',
        next_required_action: 'build_entry_field',
        ready_for_match_schedule: false,
        effective_draw_fingerprint: null,
        blockers: ['tournament_entry_field_required']
      }
    ],
    ready_for_week_schedule: false,
    blockers: ['event-b:entry_field_required'],
    preparation_fingerprint: 'c'.repeat(64),
    authority_source: 'run_owned_db_authorities.v1'
  },
  canonical_preparation_ready: false,
  blockers: ['event-b:entry_field_required'],
  can_propose_schedule: false,
  expected_position_fingerprint: 'b'.repeat(64),
  preflight_fingerprint: 'd'.repeat(64),
  read_only: true
})

function show(snapshot: AuthoritativeWeekSchedulePreflight | undefined, enabled = true) {
  return render(
    <TournamentPreparationGuide runId="run/a" branchId="branch #1"
      preflight={snapshot} enabled={enabled} />
  )
}

describe('TournamentPreparationGuide', () => {
  it('describes distinct ready and blocked tournament states with exact encoded Run/Branch links', () => {
    show(preflight())
    const guide = screen.getByRole('region', { name: 'Tournament preparation guide' })
    expect(within(guide).getByText(/1 of 2/)).toBeInTheDocument()
    expect(within(guide).getByText('tournament_entry_field_required')).toBeInTheDocument()
    expect(within(guide).getByText(/Review eligible applications or the frozen Finals selection/)).toBeInTheDocument()
    expect(within(guide).getAllByRole('link', { name: 'Open Branch-scoped planned event review' }))
      .toHaveLength(2)
    expect(within(guide).getAllByRole('link')[0])
      .toHaveAttribute('href', '/admin/runs/run%2Fa/calendar/event%2F%CE%B1?branch=branch%20%231')
    expect(within(guide).queryByRole('button')).not.toBeInTheDocument()
  })

  it.each([
    ['adopt_ranking_snapshot', 'ranking_snapshot_required', /published Ranking Snapshot/],
    ['review_wild_cards', 'wild_card_review_required', /Wild Card/],
    ['review_pre_draw_or_commit_draw_input', 'draw_input_ready', /qualification and the pre-draw/],
    ['generate_draw', 'draw_generation_ready', /generate the canonical Draw/],
    ['prepare_group_match_schedule', 'group_match_schedule_required', /frozen group-match schedule/],
    ['review_finals_replacement', 'finals_replacement_required', /Finals participant replacement/],
    ['configure_tournament_format', 'tournament_format_required', /check which controls are implemented/],
    ['generate_tournament_topology', 'tournament_topology_required', /check which controls are implemented/]
  ] as const)('explains %s without starting any operation', (action, phase, expected) => {
    const p = preflight()
    p.canonical_preparation!.tournaments[1] = {
      ...p.canonical_preparation!.tournaments[1],
      next_required_action: action,
      phase
    }
    show(p)
    expect(screen.getByText(expected)).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('treats a deliberately unsupported knockout adapter as an engine limitation', () => {
    const p = preflight()
    p.canonical_preparation!.tournaments[1] = {
      ...p.canonical_preparation!.tournaments[1],
      phase: 'knockout_draw_adapter_required',
      next_required_action: 'none',
      blockers: ['hybrid_adapter_unavailable']
    }
    show(p)
    expect(screen.getByText(/No verified action available here/)).toBeInTheDocument()
    expect(screen.getAllByRole('link')).toHaveLength(1)
    expect(screen.getByText('hybrid_adapter_unavailable')).toBeInTheDocument()
  })

  it.each([
    ['different Run', (p: AuthoritativeWeekSchedulePreflight) => { p.run_id = 'other' }],
    ['different Branch in tournament', (p: AuthoritativeWeekSchedulePreflight) => { p.canonical_preparation!.tournaments[0].branch_id = 'other' }],
    ['missing event', (p: AuthoritativeWeekSchedulePreflight) => { p.canonical_preparation!.tournaments.pop() }],
    ['duplicate event', (p: AuthoritativeWeekSchedulePreflight) => { p.canonical_preparation!.tournaments[1].event_id = 'event/α' }],
    ['invalid fingerprint', (p: AuthoritativeWeekSchedulePreflight) => { p.preflight_fingerprint = 'broken' }],
    ['foreign preparation authority', (p: AuthoritativeWeekSchedulePreflight) => { p.canonical_preparation!.authority_source = 'legacy' as 'run_owned_db_authorities.v1' }],
    ['invalid next action', (p: AuthoritativeWeekSchedulePreflight) => {
      p.canonical_preparation!.tournaments[1].next_required_action = 'automatic_approve' as CanonicalTournamentPreparationState['next_required_action']
    }],
    ['contradictory ready summary', (p: AuthoritativeWeekSchedulePreflight) => { p.canonical_preparation!.ready_for_week_schedule = true }]
  ])('fails closed on %s', (_name, corrupt) => {
    const p = preflight()
    corrupt(p)
    show(p)
    expect(screen.getByText(/Not verified: canonical tournament preparation/)).toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('does not show event actions for a missing or disabled Branch', () => {
    show(undefined)
    expect(screen.getByText(/Not verified: canonical tournament preparation/)).toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })

  it('does not infer preparation or expose links without an active Saved Revision', () => {
    show(preflight(), false)
    expect(screen.getByText(/active Branch and Saved Revision/)).toBeInTheDocument()
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })
})
