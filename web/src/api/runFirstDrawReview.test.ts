import { describe, expect, it } from 'vitest'

import { verifiedGeneratedFirstDraw } from './runFirstDrawReview'
import type {
  CanonicalDrawBracket, CanonicalDrawSlot, CanonicalTournamentDrawAuthority,
  CanonicalTournamentDrawState, CanonicalTournamentEntryFieldState
} from './types'

// Contract projection only: no MatchEngine result or qualification winner.
function platinum() {
  const scope = { run_id: 'run', branch_id: 'branch', event_id: 'platinum' }
  const direct = Array.from({ length: 26 }, (_, i) => `M${i + 1}`)
  const qPlayers = Array.from({ length: 24 }, (_, i) => `Q-player-${i + 1}`)
  const slot = (index: number, player: string | null, placeholder: string | null = null): CanonicalDrawSlot => ({
    slot_index: index, entrant_kind: player ? 'player' : placeholder ? 'qualifier_placeholder' : 'bye',
    player_id: player, placeholder_id: placeholder, seed_number: null, is_seed_protected: false
  })
  const mainSlots = [...direct, 'WC1', 'WC2'].map((player, i) => slot(i + 1, player))
  const main: CanonicalDrawBracket = {
    draw_type: 'main', bracket_size: 32, seed_positions: [], nodes: [], bye_slot_indexes: [],
    slots: [...mainSlots, ...[1, 2, 3, 4].map(i => slot(28 + i, null, `Q${i}`))],
    qualifier_placeholder_slots: [1, 2, 3, 4].map(i => [`Q${i}`, 28 + i])
  }
  const sections: CanonicalDrawBracket[] = [1, 2, 3, 4].map(i => ({
    draw_type: 'qualification', section_id: `Q${i}`, bracket_size: 8,
    seed_positions: [], nodes: [], qualifier_placeholder_slots: [], bye_slot_indexes: [2, 6],
    slots: [
      slot(1, qPlayers[(i - 1) * 6]), slot(2, null),
      slot(3, qPlayers[(i - 1) * 6 + 1]), slot(4, qPlayers[(i - 1) * 6 + 2]),
      slot(5, qPlayers[(i - 1) * 6 + 3]), slot(6, null),
      slot(7, qPlayers[(i - 1) * 6 + 4]), slot(8, qPlayers[(i - 1) * 6 + 5])
    ]
  }))
  const field: CanonicalTournamentEntryFieldState = {
    ...scope, schema_version: 'canonical_tournament_entry_field_state.v2',
    field_sequence: 1, field_fingerprint: 'a'.repeat(64), mode: 'initial',
    direct_main_player_ids: direct, qualification_player_ids: qPlayers,
    below_qualification_cut_player_ids: ['waiting'], withdrawn_player_ids: [],
    main_draw_capacity: 32, active_main_entrant_count: 32, effective_main_bye_count: 0,
    main_diagnostics: [], draw_input_committed: true, pre_draw_repair_locked_by_draw_input: true
  }
  const state: CanonicalTournamentDrawState = {
    ...scope, schema_version: 'canonical_tournament_draw_state.v1', field_sequence: 1,
    field_fingerprint: field.field_fingerprint, main_draw_capacity: 32, active_main_entrant_count: 32,
    effective_main_bye_count: 0, draw_input_committed: true, draw_input_fingerprint: 'b'.repeat(64),
    draw_seed: 17, main_seed_count: 8, qualification_seed_count: 8, initial_draw_generated: true,
    draw_authority_fingerprint: 'c'.repeat(64), draw_algorithm_version: 'padded_qualification_sections.v3',
    main_slot_count: 32, main_node_count: 31, main_bye_count: 0,
    qualification_section_count: 4, qualification_section_sizes: [8, 8, 8, 8], main_diagnostics: []
  }
  const authority: CanonicalTournamentDrawAuthority = {
    ...scope, schema_version: 'tournament_draw_authority.v2', algorithm_version: 'padded_qualification_sections.v3',
    generated_by_command_id: 'draw', draw_input_fingerprint: state.draw_input_fingerprint!,
    main, qualification: null, qualification_sections: sections
  }
  return { field, state, authority }
}

const verify = ({ state, authority, field }: ReturnType<typeof platinum>) =>
  verifiedGeneratedFirstDraw(state, authority, field, 'b'.repeat(64), 'run', 'branch', 'platinum')

describe('initial Draw padded Qualification contract', () => {
  it('accepts Main32 and four six-player sections with two BYEs each', () => {
    expect(verify(platinum())).toBe(true)
  })

  it('refuses a version label inconsistent with the committed Draw state', () => {
    const fixture = platinum()
    fixture.state.draw_algorithm_version = 'idealized_seed_tiers.v2'
    expect(verify(fixture)).toBe(false)
  })

  it('refuses loss or duplication of a real qualification player', () => {
    const fixture = platinum()
    fixture.authority.qualification_sections![0].slots[0].player_id = 'waiting'
    expect(verify(fixture)).toBe(false)
    fixture.authority.qualification_sections![0].slots[0].player_id = 'Q-player-2'
    expect(verify(fixture)).toBe(false)
  })
})
