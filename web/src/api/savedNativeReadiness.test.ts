import { describe, expect, it } from 'vitest'
import {
  sameSavedDrawSource, validSavedDrawEntryEvidence, validSavedDrawPreflight
} from './savedNativeReadiness'
import type { SavedDrawEntryEvidence, SavedDrawPreflight } from './savedNativeReadiness'

const a = 'a'.repeat(64)
const b = 'b'.repeat(64)
const scope = { runId: 'run-a', branchId: 'branch-a' }
const preflight = (patch: Partial<SavedDrawPreflight> = {}): SavedDrawPreflight => ({
  saved_revision_id: 'rev-1', source_plan_fingerprint: a, draw_fingerprint: b,
  ranking_status: 'unranked', point_table_status: 'not_required',
  required_point_stages: [], missing_point_stages: [], invalid_point_stages: [],
  native_execution_status: 'requires_adoption_preview', ...patch
})
const evidence = (patch: Partial<SavedDrawEntryEvidence> = {}): SavedDrawEntryEvidence => ({
  saved_revision_id: 'rev-1', source_plan_fingerprint: a, event_id: 'event-x',
  entrants: [
    { player_id: 'P1', draw_role: 'direct_main', first_entry: {
      schema_version: 'player_tour_entry_trigger.v1', run_id: 'run-a', branch_id: 'branch-a',
      player_id: 'P1', event_id: 'event-x', trigger_kind: 'valid_tournament_application',
      trigger_week: { season_index: 0, week: 3 }, decision_slot_ordinal: 1,
      source_evidence_id: 'app-1', source_evidence_fingerprint: b, provenance: 'test'
    } },
    { player_id: 'P2', draw_role: 'qualification', first_entry: null }
  ], ...patch
})

describe('Saved Draw native readiness contracts (pure validators)', () => {
  it('accepts consistent Unranked and Ranked preflights', () => {
    expect(validSavedDrawPreflight(preflight(), 'rev-1')).toBe(true)
    expect(validSavedDrawPreflight(preflight({
      ranking_status: 'ranked', point_table_status: 'complete',
      required_point_stages: ['W', 'F']
    }), 'rev-1')).toBe(true)
    expect(validSavedDrawPreflight(preflight({
      ranking_status: 'ranked', point_table_status: 'incomplete',
      required_point_stages: ['W', 'F'], missing_point_stages: ['F'],
      native_execution_status: 'ranked_points_incomplete'
    }), 'rev-1')).toBe(true)
  })

  it('rejects another revision, malformed hashes and contradictory statuses', () => {
    expect(validSavedDrawPreflight(preflight(), 'rev-2')).toBe(false)
    expect(validSavedDrawPreflight(preflight({ draw_fingerprint: 'short' }), 'rev-1')).toBe(false)
    expect(validSavedDrawPreflight(preflight({ point_table_status: 'complete' }), 'rev-1')).toBe(false)
    // Gaps cannot be presented as ready for an adoption preview.
    expect(validSavedDrawPreflight(preflight({
      ranking_status: 'ranked', point_table_status: 'incomplete',
      required_point_stages: ['W'], missing_point_stages: ['W']
    }), 'rev-1')).toBe(false)
    // A complete table cannot be reported as incomplete.
    expect(validSavedDrawPreflight(preflight({
      ranking_status: 'ranked', point_table_status: 'complete',
      required_point_stages: ['W'], native_execution_status: 'ranked_points_incomplete'
    }), 'rev-1')).toBe(false)
    // Reported gaps must be stages the Draw actually requires.
    expect(validSavedDrawPreflight(preflight({
      ranking_status: 'ranked', point_table_status: 'incomplete',
      required_point_stages: ['W'], missing_point_stages: ['F'],
      native_execution_status: 'ranked_points_incomplete'
    }), 'rev-1')).toBe(false)
    expect(validSavedDrawPreflight(null, 'rev-1')).toBe(false)
  })

  it('requires exact scope, unique players and matching trigger identity', () => {
    expect(validSavedDrawEntryEvidence(evidence(), 'rev-1', 'event-x', scope)).toBe(true)
    expect(validSavedDrawEntryEvidence(evidence(), 'rev-2', 'event-x', scope)).toBe(false)
    expect(validSavedDrawEntryEvidence(evidence(), 'rev-1', 'event-y', scope)).toBe(false)
    expect(validSavedDrawEntryEvidence(evidence(), 'rev-1', 'event-x',
      { runId: 'run-b', branchId: 'branch-a' })).toBe(false)
    const duplicate = evidence()
    duplicate.entrants[1] = { ...duplicate.entrants[1], player_id: 'P1' }
    expect(validSavedDrawEntryEvidence(duplicate, 'rev-1', 'event-x', scope)).toBe(false)
    const foreign = evidence()
    foreign.entrants[0].first_entry!.player_id = 'P9'
    expect(validSavedDrawEntryEvidence(foreign, 'rev-1', 'event-x', scope)).toBe(false)
    const unknownRole = evidence()
    ;(unknownRole.entrants[1] as { draw_role: string }).draw_role = 'lucky_loser'
    expect(validSavedDrawEntryEvidence(unknownRole, 'rev-1', 'event-x', scope)).toBe(false)
    const badWeek = evidence()
    badWeek.entrants[0].first_entry!.trigger_week.week = 0
    expect(validSavedDrawEntryEvidence(badWeek, 'rev-1', 'event-x', scope)).toBe(false)
  })

  it('binds both inspections to one authenticated Draw source', () => {
    expect(sameSavedDrawSource(preflight(), evidence())).toBe(true)
    expect(sameSavedDrawSource(preflight(), evidence({ source_plan_fingerprint: b }))).toBe(false)
    expect(sameSavedDrawSource(preflight(), evidence({ saved_revision_id: 'rev-2' }))).toBe(false)
  })
})
