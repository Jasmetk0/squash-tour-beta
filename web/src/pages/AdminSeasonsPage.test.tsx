import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminSeasonsPage } from './AdminSeasonsPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getSeasonActivePlayers: vi.fn(),
  getSeasonRegistry: vi.fn(),
  getAdminRankingTable: vi.fn(),
  getViewerRankingTable: vi.fn(),
  getAdminRankingSnapshot: vi.fn(),
  getAdminPointBreakdown: vi.fn(),
  getViewerPointBreakdown: vi.fn(),
  bootstrapSeasonFromInitialPool: vi.fn(),
  getSeasonCalendar: vi.fn(),
  getSeasonLifecycle: vi.fn(),
  getEventLifecycle: vi.fn(),
  buildSeasonCalendar: vi.fn(),
  getEventEntryList: vi.fn(),
  generateEventEntryList: vi.fn(),
  getEventDrawPackage: vi.fn(),
  generateEventDrawPackage: vi.fn(),
  getEventMatchPackage: vi.fn(),
  generateEventMatchPackage: vi.fn(),
  simulateNextEventMatch: vi.fn(),
  simulateEventMatch: vi.fn(),
  getEventProgressionStatus: vi.fn(),
  processEventByes: vi.fn(),
  refreshEventProgression: vi.fn(),
  promoteEventQualifiers: vi.fn(),
  simulateEventRound: vi.fn(),
  simulateEventDraw: vi.fn(),
  getEventResultPackage: vi.fn(),
  extractEventResultPackage: vi.fn(),
  getEventPointAwards: vi.fn(),
  generateEventPointAwards: vi.fn(),
  applyEventPointAwards: vi.fn(),
  simulateOneEvent: vi.fn(),
  preflightSeasonWeek: vi.fn(),
  runSeasonWeek: vi.fn(),
  recoverSeasonWeek: vi.fn(),
  getSeasonReadiness: vi.fn(),
  preflightSeasonRange: vi.fn(),
  runSeasonRange: vi.fn(),
  ApiError: class ApiError extends Error { status = 400 }
}))

vi.mock('../api/client', () => api)

const player = {
  player_id: 'P-2000-AAA-0001',
  name: 'Adam Ahmed AA01',
  country_code: 'AAA',
  nationality: 'AAA',
  birth_year: 1976,
  birth_year_week: 12,
  age_years_at_season_start: 24,
  age_weeks_at_season_start: 1240,
  current_ability: 78,
  potential_ability: 88,
  potential_tier: 'A',
  career_stage: 'prime',
  play_style: 'balanced',
  archetype: 'all_court',
  attributes: { technique: 78, movement: 77, physical: 76, mental: 79, consistency: 78, clutch: 75, recovery: 77 },
  hidden_career_traits: { potential_ceiling: 88, growth_curve: 'steady', professionalism: 0.8, ambition: 0.7, travel_tolerance: 0.6, schedule_aggression: 0.5, injury_proneness: 0.2, resilience: 0.7 },
  health_status: 'fresh',
  active_status: 'active',
  ranking_points: 0,
  race_points: 0,
  protected_ranking_points: 0,
  season: '2000/2001',
  source_pool_player_id: 'P-2000-AAA-0001',
  source_generation_fingerprint: 'source-fp',
  source_generation: 'initial_pool',
  manual_override: false,
  locked_from_initial_pool: true,
  bootstrap_fingerprint: 'player-boot-fp',
  bootstrap_seed: 12345,
  bootstrap_id: 'BOOT-2000-test'
}

const response = {
  players: [player],
  summary: {
    total_active_players: 1,
    countries_represented: 1,
    manual_players: 0,
    generated_players: 1,
    locked_from_initial_pool: 1,
    average_current_ability: 78,
    average_potential_ability: 88,
    by_potential_tier: { A: 1 }
  },
  metadata: {
    season: '2000/2001',
    source_season: '2000/2001',
    bootstrap_seed: 12345,
    dry_run: true,
    overwrite_existing: false,
    source_initial_pool_fingerprint: 'pool-fp',
    bootstrap_id: 'BOOT-2000-test',
    bootstrap_fingerprint: 'boot-fp',
    player_count: 1,
    persistence_path: null,
    ranking_seeding_implemented: false
  },
  warnings: ['Source initial pool is very small for a professional tour bootstrap.']
}

const empty = {
  players: [],
  summary: { total_active_players: 0, countries_represented: 0, manual_players: 0, generated_players: 0, locked_from_initial_pool: 0, average_current_ability: 0, average_potential_ability: 0, by_potential_tier: {} },
  metadata: null,
  warnings: []
}

const calendarEvent = {
  event_id: 'EVT-2000-W01-wt_a',
  season: '2000/2001',
  season_week: 1,
  calendar_year: 2000,
  year_week: 37,
  template_id: 'wt_a',
  event_name: 'World A',
  category: 'PLATINUM',
  tour_level: 'WORLD_TOUR',
  host_country: 'ENG',
  host_city: null,
  region: 'EUROPE',
  duration_in_season_weeks: 1,
  start_season_week: 1,
  end_season_week: 1,
  status: 'planned',
  main_draw_size: 32,
  qualification_draw_size: 16,
  seeds_count: 8,
  qualifier_spots: 4,
  wild_cards: 2,
  byes: 0,
  point_distribution_ref: 'world',
  point_distribution: null,
  prize_money: 100000,
  prestige: 9,
  event_level_overrides: {},
  source_template_fingerprint: 'template-fp',
  template_snapshot_fingerprint: 'template-fp',
  calendar_fingerprint: 'calendar-fp',
  template_snapshot: { template_id: 'wt_a' }
}

const emptyCalendar = {
  calendar: null,
  summary: { event_count: 0, season_weeks_used: 0, first_event_week: null, last_event_week: null, world_tour_events: 0, elite_tour_events: 0, validation_warning_count: 0, validation_error_count: 0, persisted: false, calendar_exists: false },
  metadata: null,
  validation_warnings: [],
  validation_errors: []
}


const emptyEntryResult = {
  entry_list: null,
  summary: { total_active_players: 0, considered_players: 0, entered_players: 0, main_draw_acceptances: 0, qualification_acceptances: 0, alternates: 0, rejected_or_not_entered: 0, countries_represented: 0, average_entry_probability: 0, average_quality_score: 0, validation_warning_count: 0, validation_error_count: 0 },
  metadata: null,
  validation_warnings: [],
  validation_errors: [],
  entry_list_exists: false
}

const entryResult = {
  entry_list: {
    event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', season_week: 1, calendar_year: 2000, year_week: 37, template_id: 'wt_a', generated_from_calendar_fingerprint: 'calendar-fp', generated_from_active_players_fingerprint: 'active-fp', seed: 12345, dry_run: true, persisted: false,
    entries: [{ entry_id: 'entry-1', player_id: 'P-2000-AAA-0001', name: 'Adam Ahmed AA01', country_code: 'AAA', ranking_points: 0, race_points: 0, current_ability: 78, potential_ability: 88, entry_probability: 0.75, entry_score: 1.2, quality_score: 0.8, travel_score: 1, decision: 'accepted_main_draw', acceptance_status: 'accepted_main_draw', ranking_priority: 1, seed_candidate_rank: 1, source_player_fingerprint: 'source-fp', bootstrap_fingerprint: 'player-boot-fp', generated_fingerprint: 'entry-fp', reason: 'direct main draw acceptance', decision_notes: 'EntryEngine target=MAIN' }],
    summary: { total_active_players: 1, considered_players: 1, entered_players: 1, main_draw_acceptances: 1, qualification_acceptances: 0, alternates: 0, rejected_or_not_entered: 0, countries_represented: 1, average_entry_probability: 0.75, average_quality_score: 0.8, validation_warning_count: 1, validation_error_count: 1 },
    metadata: { event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', seed: 12345, dry_run: true, persisted: false, build_fingerprint: 'entry-build-fp', active_players_fingerprint: 'active-fp', calendar_event_fingerprint: 'calendar-fp', ranking_basis: 'current zero-points bootstrap', persistence_path: null },
    validation_warnings: [{ severity: 'warning', code: 'entry_warn', message: 'entry warning', event_id: 'EVT-2000-W01-wt_a', player_id: null, field: null }],
    validation_errors: [{ severity: 'error', code: 'entry_error', message: 'entry error', event_id: 'EVT-2000-W01-wt_a', player_id: 'P-2000-AAA-0001', field: 'season_week' }]
  },
  summary: { total_active_players: 1, considered_players: 1, entered_players: 1, main_draw_acceptances: 1, qualification_acceptances: 0, alternates: 0, rejected_or_not_entered: 0, countries_represented: 1, average_entry_probability: 0.75, average_quality_score: 0.8, validation_warning_count: 1, validation_error_count: 1 },
  metadata: { event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', seed: 12345, dry_run: true, persisted: false, build_fingerprint: 'entry-build-fp', active_players_fingerprint: 'active-fp', calendar_event_fingerprint: 'calendar-fp', ranking_basis: 'current zero-points bootstrap', persistence_path: null },
  validation_warnings: [{ severity: 'warning', code: 'entry_warn', message: 'entry warning', event_id: 'EVT-2000-W01-wt_a', player_id: null, field: null }],
  validation_errors: [{ severity: 'error', code: 'entry_error', message: 'entry error', event_id: 'EVT-2000-W01-wt_a', player_id: 'P-2000-AAA-0001', field: 'season_week' }],
  entry_list_exists: false
}


const emptyDrawResult = {
  draw_package: null,
  summary: { event_id: null, main_draw_size: 0, qualification_draw_size: 0, main_draw_players: 0, qualification_draw_players: 0, qualifier_placeholders: 0, byes: 0, seeds: 0, validation_warning_count: 0, validation_error_count: 0 },
  metadata: null,
  validation_warnings: [],
  validation_errors: [],
  draw_package_exists: false
}

const drawResult = {
  draw_package: {
    event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', template_id: 'wt_a', season_week: 1, calendar_year: 2000, year_week: 37, seed: 12345, dry_run: true, persisted: false,
    qualification_draw: { draw_id: 'EVT-2000-W01-wt_a:qualification', draw_type: 'qualification', draw_size: 2, round_count: 1, generated_fingerprint: 'qual-fp', seeds: [], byes: [], qualifier_placeholders: [], rounds: [{ round_number: 1, round_name: 'Round 1', match_count: 1, matches: [{ match_id: 'qm1', round_number: 1, bracket_position: 1, top_slot_id: 'qs1', bottom_slot_id: 'qs2', top_source: 'SLOT:1', bottom_source: 'SLOT:2', winner_to_match_id: null, status: 'pending' }] }], slots: [{ slot_id: 'qs1', bracket_position: 1, player_id: 'P-2000-BBB-0002', player_name: 'Ben Beta BB02', country_code: 'BBB', entry_decision: 'accepted_qualification', seed_number: null, source_entry_id: 'entry-q1', source_entry_fingerprint: 'entry-q-fp', is_bye: false, is_qualifier_placeholder: false }, { slot_id: 'qs2', bracket_position: 2, player_id: null, player_name: null, country_code: null, entry_decision: 'bye', seed_number: null, source_entry_id: null, source_entry_fingerprint: null, is_bye: true, is_qualifier_placeholder: false }] },
    main_draw: { draw_id: 'EVT-2000-W01-wt_a:main', draw_type: 'main', draw_size: 4, round_count: 2, generated_fingerprint: 'main-fp', seeds: [{ seed_number: 1, player_id: 'P-2000-AAA-0001', player_name: 'Adam Ahmed AA01', ranking_priority: 1, placement_position: 1 }], byes: [{ slot_id: 'ms4', bracket_position: 4 }], qualifier_placeholders: [{ placeholder_id: 'Q1', slot_id: 'ms2', bracket_position: 2, qualifier_index: 1 }], rounds: [{ round_number: 1, round_name: 'Round 1', match_count: 2, matches: [{ match_id: 'm1', round_number: 1, bracket_position: 1, top_slot_id: 'ms1', bottom_slot_id: 'ms2', top_source: 'SLOT:1', bottom_source: 'SLOT:2', winner_to_match_id: 'R2-N1', status: 'pending' }, { match_id: 'm2', round_number: 1, bracket_position: 2, top_slot_id: 'ms3', bottom_slot_id: 'ms4', top_source: 'SLOT:3', bottom_source: 'SLOT:4', winner_to_match_id: 'R2-N1', status: 'bye_pending' }] }], slots: [{ slot_id: 'ms1', bracket_position: 1, player_id: 'P-2000-AAA-0001', player_name: 'Adam Ahmed AA01', country_code: 'AAA', entry_decision: 'accepted_main_draw', seed_number: 1, source_entry_id: 'entry-1', source_entry_fingerprint: 'entry-fp', is_bye: false, is_qualifier_placeholder: false }, { slot_id: 'ms2', bracket_position: 2, player_id: null, player_name: null, country_code: null, entry_decision: 'qualifier_placeholder', seed_number: null, source_entry_id: 'q-placeholder', source_entry_fingerprint: 'q-fp', is_bye: false, is_qualifier_placeholder: true }, { slot_id: 'ms3', bracket_position: 3, player_id: null, player_name: null, country_code: null, entry_decision: 'wild_card_reserved', seed_number: null, source_entry_id: 'wc-placeholder', source_entry_fingerprint: 'wc-fp', is_bye: false, is_qualifier_placeholder: false }, { slot_id: 'ms4', bracket_position: 4, player_id: null, player_name: null, country_code: null, entry_decision: 'bye', seed_number: null, source_entry_id: null, source_entry_fingerprint: null, is_bye: true, is_qualifier_placeholder: false }] },
    summary: { event_id: 'EVT-2000-W01-wt_a', main_draw_size: 4, qualification_draw_size: 2, main_draw_players: 1, qualification_draw_players: 1, qualifier_placeholders: 1, byes: 2, seeds: 1, validation_warning_count: 1, validation_error_count: 1 },
    metadata: { event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', seed: 12345, dry_run: true, persisted: false, build_fingerprint: 'draw-build-fp', entry_list_fingerprint: 'entry-build-fp', calendar_event_fingerprint: 'calendar-fp', draw_engine_version: 'draw_engine_v1', persistence_path: null, ranking_basis: 'current zero-points bootstrap' },
    validation_warnings: [{ severity: 'warning', code: 'draw_warn', message: 'draw warning', event_id: 'EVT-2000-W01-wt_a', player_id: null, field: null }],
    validation_errors: [{ severity: 'error', code: 'draw_error', message: 'draw error', event_id: 'EVT-2000-W01-wt_a', player_id: null, field: null }]
  },
  summary: { event_id: 'EVT-2000-W01-wt_a', main_draw_size: 4, qualification_draw_size: 2, main_draw_players: 1, qualification_draw_players: 1, qualifier_placeholders: 1, byes: 2, seeds: 1, validation_warning_count: 1, validation_error_count: 1 },
  metadata: { event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', seed: 12345, dry_run: true, persisted: false, build_fingerprint: 'draw-build-fp', entry_list_fingerprint: 'entry-build-fp', calendar_event_fingerprint: 'calendar-fp', draw_engine_version: 'draw_engine_v1', persistence_path: null, ranking_basis: 'current zero-points bootstrap' },
  validation_warnings: [{ severity: 'warning', code: 'draw_warn', message: 'draw warning', event_id: 'EVT-2000-W01-wt_a', player_id: null, field: null }],
  validation_errors: [{ severity: 'error', code: 'draw_error', message: 'draw error', event_id: 'EVT-2000-W01-wt_a', player_id: null, field: null }],
  draw_package_exists: false
}


const emptyMatchResult = {
  match_package: null,
  summary: { event_id: null, total_matches: 0, qualification_matches: 0, main_draw_matches: 0, pending_matches: 0, completed_matches: 0, blocked_matches: 0, bye_auto_advances: 0, validation_warning_count: 0, validation_error_count: 0 },
  metadata: null,
  validation_warnings: [],
  validation_errors: [],
  match_package_exists: false
}

const matchRecord = {
  match_id: 'm1', event_id: 'EVT-2000-W01-wt_a', draw_type: 'main', round_number: 1, round_name: 'Round 1', bracket_position: 1, top_slot_id: 'ms1', bottom_slot_id: 'ms2', top_source: 'SLOT:1', bottom_source: 'SLOT:2', top_player_id: 'P-2000-AAA-0001', bottom_player_id: 'P-2000-BBB-0002', top_player_name: 'Adam Ahmed AA01', bottom_player_name: 'Ben Beta BB02', top_country_code: 'AAA', bottom_country_code: 'BBB', status: 'pending', winner_player_id: null, loser_player_id: null, scoreline: null, simulated_result: null, winner_to_match_id: 'm3', source_draw_fingerprint: 'draw-fp', generated_fingerprint: 'match-fp', result_fingerprint: null, simulation_seed: null, result_notes: null
}

const completedMatchRecord = {
  ...matchRecord,
  status: 'completed',
  winner_player_id: 'P-2000-AAA-0001',
  loser_player_id: 'P-2000-BBB-0002',
  scoreline: '11-7, 11-8, 11-9',
  result_fingerprint: 'result-fp',
  simulation_seed: 999,
  result_notes: 'ranking/race updates not implemented',
  simulated_result: { match_id: 'm1', winner_player_id: 'P-2000-AAA-0001', loser_player_id: 'P-2000-BBB-0002', scoreline: '11-7, 11-8, 11-9', games: [], points_summary: {}, retired: false, walkover: false, simulation_fingerprint: 'result-fp', seed: 999 }
}

const matchResult = {
  match_package: {
    event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', template_id: 'wt_a', season_week: 1, calendar_year: 2000, year_week: 37, seed: 12345, dry_run: true, persisted: false, qualification_matches: [], main_draw_matches: [matchRecord],
    summary: { event_id: 'EVT-2000-W01-wt_a', total_matches: 1, qualification_matches: 0, main_draw_matches: 1, pending_matches: 1, completed_matches: 0, blocked_matches: 0, bye_auto_advances: 0, validation_warning_count: 1, validation_error_count: 1 },
    metadata: { event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', seed: 12345, dry_run: true, persisted: false, build_fingerprint: 'match-build-fp', draw_package_fingerprint: 'draw-build-fp', active_players_fingerprint: 'active-fp', match_engine_version: 'match_engine_v1', persistence_path: null, ranking_updates_implemented: false, qualification_winners_promoted: false },
    validation_warnings: [{ severity: 'warning', code: 'match_warn', message: 'match warning', event_id: 'EVT-2000-W01-wt_a', match_id: 'm1', player_id: null, field: null }],
    validation_errors: [{ severity: 'error', code: 'match_error', message: 'match error', event_id: 'EVT-2000-W01-wt_a', match_id: 'm1', player_id: null, field: null }]
  },
  summary: { event_id: 'EVT-2000-W01-wt_a', total_matches: 1, qualification_matches: 0, main_draw_matches: 1, pending_matches: 1, completed_matches: 0, blocked_matches: 0, bye_auto_advances: 0, validation_warning_count: 1, validation_error_count: 1 },
  metadata: { event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', seed: 12345, dry_run: true, persisted: false, build_fingerprint: 'match-build-fp', draw_package_fingerprint: 'draw-build-fp', active_players_fingerprint: 'active-fp', match_engine_version: 'match_engine_v1', persistence_path: null, ranking_updates_implemented: false, qualification_winners_promoted: false },
  validation_warnings: [{ severity: 'warning', code: 'match_warn', message: 'match warning', event_id: 'EVT-2000-W01-wt_a', match_id: 'm1', player_id: null, field: null }],
  validation_errors: [{ severity: 'error', code: 'match_error', message: 'match error', event_id: 'EVT-2000-W01-wt_a', match_id: 'm1', player_id: null, field: null }],
  match_package_exists: false
}

const simulatedMatchResult = {
  ...matchResult,
  match_package: { ...matchResult.match_package, main_draw_matches: [completedMatchRecord], summary: { ...matchResult.match_package.summary, pending_matches: 0, completed_matches: 1 } },
  summary: { ...matchResult.summary, pending_matches: 0, completed_matches: 1 },
  match_package_exists: true
}


const emptyEventResult = {
  result_package: null,
  summary: null,
  metadata: null,
  validation_warnings: [],
  validation_errors: [],
  result_package_exists: false
}

const eventResult = {
  result_package: {
    event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', template_id: 'wt_a', season_week: 1, calendar_year: 2000, year_week: 37, event_name: 'World A', category: 'PLATINUM', tour_level: 'WORLD_TOUR', host_country: 'ENG', seed: 12345, dry_run: true, persisted: false, completion_status: 'complete',
    champion: { player_id: 'P-2000-AAA-0001', player_name: 'Adam Ahmed AA01', country_code: 'AAA', seed_number: 1, entry_decision: 'accepted_main_draw', qualifier: false, wildcard: false, ranking_priority: 1 },
    finalist: { player_id: 'P-2000-BBB-0002', player_name: 'Ben Beta BB02', country_code: 'BBB', seed_number: null, entry_decision: 'accepted_qualification', qualifier: true, wildcard: false, ranking_priority: null },
    semifinalists: [{ player_id: 'P-2000-CCC-0003', player_name: 'Carl Cairo CC03', country_code: 'CCC', seed_number: null, entry_decision: 'accepted_main_draw', qualifier: false, wildcard: false, ranking_priority: null }],
    quarterfinalists: [],
    qualification_winners: [{ player_id: 'P-2000-BBB-0002', player_name: 'Ben Beta BB02', country_code: 'BBB', seed_number: null, entry_decision: 'accepted_qualification', qualifier: true, wildcard: false, ranking_priority: null }],
    player_results: [
      { player_id: 'P-2000-AAA-0001', player_name: 'Adam Ahmed AA01', country_code: 'AAA', draw_type: 'main', entry_decision: 'accepted_main_draw', seed_number: 1, qualifier: false, reached_stage: 'champion', final_round_number: 2, eliminated_by_player_id: null, eliminated_by_player_name: null, last_match_id: 'm3', wins: 2, losses: 0, walkovers_received: 0, byes_received: 0, retired_or_walkover_loss: false, points_awarded: 0, race_points_awarded: 0, prize_money_awarded: 0 },
      { player_id: 'P-2000-BBB-0002', player_name: 'Ben Beta BB02', country_code: 'BBB', draw_type: 'both', entry_decision: 'accepted_qualification', seed_number: null, qualifier: true, reached_stage: 'finalist', final_round_number: 2, eliminated_by_player_id: 'P-2000-AAA-0001', eliminated_by_player_name: 'Adam Ahmed AA01', last_match_id: 'm3', wins: 2, losses: 1, walkovers_received: 0, byes_received: 0, retired_or_walkover_loss: false, points_awarded: 0, race_points_awarded: 0, prize_money_awarded: 0 }
    ],
    match_result_refs: [{ match_id: 'm3', draw_type: 'main', round_number: 2, round_name: 'Final', bracket_position: 1, winner_player_id: 'P-2000-AAA-0001', loser_player_id: 'P-2000-BBB-0002', scoreline: '11-7, 11-8, 11-9', result_fingerprint: 'result-fp' }],
    summary: { event_id: 'EVT-2000-W01-wt_a', completion_status: 'complete', player_count: 2, main_draw_player_count: 2, qualification_player_count: 1, completed_matches: 3, incomplete_matches: 0, champion_player_id: 'P-2000-AAA-0001', finalist_player_id: 'P-2000-BBB-0002', qualification_winner_count: 1, ranking_points_awarded_total: 0, race_points_awarded_total: 0, validation_warning_count: 1, validation_error_count: 1 },
    metadata: { event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', seed: 12345, dry_run: true, persisted: false, build_fingerprint: 'result-build-fp', match_package_fingerprint: 'match-build-fp', draw_package_fingerprint: 'draw-build-fp', calendar_event_fingerprint: 'calendar-fp', ranking_updates_implemented: false, points_awarding_implemented: false, persistence_path: null },
    validation_warnings: [{ severity: 'warning', code: 'result_warn', message: 'result warning', event_id: 'EVT-2000-W01-wt_a', match_id: null, player_id: null, field: null }],
    validation_errors: [{ severity: 'error', code: 'result_error', message: 'result error', event_id: 'EVT-2000-W01-wt_a', match_id: null, player_id: 'P-2000-BBB-0002', field: null }]
  },
  summary: { event_id: 'EVT-2000-W01-wt_a', completion_status: 'complete', player_count: 2, main_draw_player_count: 2, qualification_player_count: 1, completed_matches: 3, incomplete_matches: 0, champion_player_id: 'P-2000-AAA-0001', finalist_player_id: 'P-2000-BBB-0002', qualification_winner_count: 1, ranking_points_awarded_total: 0, race_points_awarded_total: 0, validation_warning_count: 1, validation_error_count: 1 },
  metadata: { event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', seed: 12345, dry_run: true, persisted: false, build_fingerprint: 'result-build-fp', match_package_fingerprint: 'match-build-fp', draw_package_fingerprint: 'draw-build-fp', calendar_event_fingerprint: 'calendar-fp', ranking_updates_implemented: false, points_awarding_implemented: false, persistence_path: null },
  validation_warnings: [{ severity: 'warning', code: 'result_warn', message: 'result warning', event_id: 'EVT-2000-W01-wt_a', match_id: null, player_id: null, field: null }],
  validation_errors: [{ severity: 'error', code: 'result_error', message: 'result error', event_id: 'EVT-2000-W01-wt_a', match_id: null, player_id: 'P-2000-BBB-0002', field: null }],
  result_package_exists: false
}

const progressionStatus = {
  event_id: 'EVT-2000-W01-wt_a',
  season: '2000/2001',
  qualification_status: 'not_applicable',
  main_draw_status: 'in_progress',
  event_status: 'in_progress',
  qualification_winners_ready: false,
  qualification_winners_promoted: false,
  pending_matches: 1,
  blocked_matches: 0,
  completed_matches: 0,
  bye_auto_advances_pending: 0,
  champion_player_id: 'P-2000-AAA-0001',
  champion_name: 'Adam Ahmed AA01',
  finalist_player_id: 'P-2000-BBB-0002',
  finalist_name: 'Ben Beta BB02',
  warnings: [{ severity: 'warning', code: 'progression_warn', message: 'progression warning', event_id: 'EVT-2000-W01-wt_a', match_id: null, player_id: null, field: null }],
  errors: []
}

const progressionResult = {
  event_id: 'EVT-2000-W01-wt_a',
  action: 'simulate_round',
  match_package: simulatedMatchResult.match_package,
  progression_status: { ...progressionStatus, completed_matches: 1, pending_matches: 0 },
  changed_match_ids: ['m1'],
  promoted_player_ids: ['P-2000-AAA-0001'],
  validation_warnings: [{ severity: 'warning', code: 'progression_warn', message: 'progression warning', event_id: 'EVT-2000-W01-wt_a', match_id: null, player_id: null, field: null }],
  validation_errors: [],
  metadata: { build_fingerprint: 'match-build-fp' }
}

const calendarResponse = {
  calendar: { season: '2000/2001', events: [calendarEvent], metadata: null, validation_warnings: [{ severity: 'warning', code: 'ranking_race_not_integrated', message: 'ranking/race integration not implemented yet', event_id: null, field: null }], validation_errors: [] },
  summary: { event_count: 1, season_weeks_used: 1, first_event_week: 1, last_event_week: 1, world_tour_events: 1, elite_tour_events: 0, validation_warning_count: 1, validation_error_count: 0, persisted: false, calendar_exists: false },
  metadata: { season: '2000/2001', season_start_calendar_year: 2000, season_start_year_week: 37, total_season_weeks: 61, event_count: 1, build_seed: 12345, build_fingerprint: 'calendar-fp', source_template_count: 1, persistence_path: null, dry_run: true, overwrite_existing: false },
  validation_warnings: [{ severity: 'warning', code: 'ranking_race_not_integrated', message: 'ranking/race integration not implemented yet', event_id: null, field: null }],
  validation_errors: [{ severity: 'error', code: 'example_error', message: 'example error', event_id: null, field: null }]
}


const lifecycleResponse = {
  season: '2000/2001',
  events: [{
    event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', season_week: 1, calendar_year: 2000, year_week: 37, event_name: 'World A', category: 'PLATINUM', tour_level: 'WORLD_TOUR', host_country: 'ENG', template_id: 'wt_a',
    current_stage: 'entries_generated', next_recommended_action: 'generate_draw', is_blocked: true, block_reasons: ['entries artifact has 1 validation error(s)'],
    entries: { exists: true, persisted: true, fingerprint: 'entry-build-fingerprint', validation_error_count: 1, validation_warning_count: 0, summary: {} },
    draw: { exists: false, persisted: false, fingerprint: null, validation_error_count: 0, validation_warning_count: 0, summary: null },
    matches: { exists: false, persisted: false, fingerprint: null, validation_error_count: 0, validation_warning_count: 0, summary: null },
    progression_status: null,
    results: { exists: false, persisted: false, fingerprint: null, validation_error_count: 0, validation_warning_count: 0, summary: null },
    point_awards: { exists: false, persisted: false, fingerprint: null, validation_error_count: 0, validation_warning_count: 0, summary: null },
    points_applied: false,
    ranking_snapshot: { exists: false, persisted: false, fingerprint: null, validation_error_count: 0, validation_warning_count: 0, summary: null },
    validation_warnings: [], validation_errors: ['entries artifact has 1 validation error(s)']
  }],
  summary: { season: '2000/2001', event_count: 1, planned_count: 0, entries_generated_count: 1, draw_generated_count: 0, matches_generated_count: 0, in_progress_count: 0, completed_count: 0, results_extracted_count: 0, points_generated_count: 0, points_applied_count: 0, ranking_snapshot_published_count: 0, blocked_count: 1 },
  metadata: { season: '2000/2001', source: 'persisted_artifact_registries', calendar_fingerprint: 'calendar-fp', generated_fingerprint: 'lifecycle-fp', read_only: true },
  validation_warnings: [],
  validation_errors: []
}

const simulateOneEventResult = {
  report: {
    event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', season_week: 1, calendar_year: 2000, year_week: 37, event_name: 'World A', seed: 12345, dry_run: true, requested_apply_points: false, requested_publish_snapshot: false,
    initial_lifecycle: lifecycleResponse.events[0],
    final_lifecycle: { ...lifecycleResponse.events[0], current_stage: 'points_generated', next_recommended_action: 'apply_point_awards', is_blocked: false, block_reasons: [] },
    steps: [
      { step: 'preflight_lifecycle', status: 'succeeded', action_detail: 'Initial lifecycle stage is planned.', artifact_exists_before: null, artifact_exists_after: null, changed_ids: [], fingerprint: 'lifecycle-fp', warnings: [], errors: [], lifecycle_stage_before_step: 'planned', lifecycle_stage_after_step: 'planned', stop_reason: null, service_called: 'SeasonEventLifecycleService.get_event_lifecycle', request_seed: null, mutates_active_players: false, mutates_ranking_snapshot: false },
      { step: 'generate_entries', status: 'planned', action_detail: 'Dry-run plan only; no mutating service was called.', artifact_exists_before: false, artifact_exists_after: false, changed_ids: [], fingerprint: null, warnings: ['sim warning'], errors: [], lifecycle_stage_before_step: 'planned', lifecycle_stage_after_step: 'planned', stop_reason: null, service_called: null, request_seed: 555, mutates_active_players: false, mutates_ranking_snapshot: false },
      { step: 'generate_point_awards', status: 'succeeded', action_detail: 'Generated event point awards.', artifact_exists_before: false, artifact_exists_after: true, changed_ids: ['EVT-2000-W01-wt_a'], fingerprint: 'points-fingerprint-abcdef', warnings: [], errors: ['sim error'], lifecycle_stage_before_step: 'results_extracted', lifecycle_stage_after_step: 'points_generated', stop_reason: null, service_called: 'SeasonPointAwardsService.generate_event_point_awards', request_seed: 777, mutates_active_players: false, mutates_ranking_snapshot: false }
    ],
    changed_artifacts: { entries: true, draw: true, matches: true, results: true, point_awards: true, active_player_points: false, ranking_snapshot: false },
    plan_summary: { planned_step_count: 1, executed_step_count: 1, skipped_step_count: 0, succeeded_step_count: 1, failed_step_count: 0, blocked_step_count: 0, first_failed_step: null, stop_reason: 'dry_run_plan_only', next_safe_action: 'run_event_simulation' },
    artifact_state_before: { entries_exists: false, draw_exists: false, matches_exists: false, results_exists: false, point_awards_exists: false, points_applied: false, ranking_snapshot_exists: false },
    artifact_state_after: { entries_exists: true, draw_exists: true, matches_exists: true, results_exists: true, point_awards_exists: true, points_applied: false, ranking_snapshot_exists: false },
    lifecycle_stage_before: 'planned',
    lifecycle_stage_after: 'points_generated',
    lifecycle_next_action_after: 'apply_point_awards',
    can_continue: true,
    safe_to_rerun: true,
    would_duplicate_points: false,
    would_overwrite_existing: false,
    completed: true,
    blocked: false,
    validation_warnings: ['report warning'],
    validation_errors: ['report error'],
    metadata: { build_fingerprint: 'sim-fp', read_only: false, lifecycle_preflight_fingerprint: 'lifecycle-fp', final_lifecycle_fingerprint: 'final-fp' }
  },
  validation_warnings: ['top warning'],
  validation_errors: []
}


const weekPreflightResult = {
  season: '2000/2001',
  season_week: 1,
  calendar_year: 2000,
  year_week: 37,
  events: [{
    event_id: 'EVT-2000-W01-wt_a',
    event_name: 'World A',
    season: '2000/2001',
    season_week: 1,
    calendar_year: 2000,
    year_week: 37,
    category: 'PLATINUM',
    tour_level: 'WORLD_TOUR',
    host_country: 'ENG',
    lifecycle_stage_before: 'planned',
    next_recommended_action_before: 'generate_entries',
    one_event_report: simulateOneEventResult.report,
    blocked: false,
    can_continue: true,
    stop_reason: 'dry_run_plan_only',
    planned_step_count: 1,
    planned_mutates_active_players: false,
    planned_mutates_ranking_snapshot: false,
    warnings: ['event warning'],
    errors: []
  }],
  summary: {
    season: '2000/2001', season_week: 1, calendar_year: 2000, year_week: 37,
    event_count: 1, planned_event_count: 1, completed_event_count: 0, blocked_event_count: 0,
    can_run_week: true, would_apply_points: false, would_publish_snapshot: false, snapshot_already_exists: false,
    week_has_multiple_events: false, total_planned_steps: 1, total_planned_player_mutations: 0, total_planned_snapshot_mutations: 0,
    first_blocked_event_id: null, stop_reason: null, next_safe_action: 'run_week_simulation'
  },
  metadata: { season: '2000/2001', season_week: 1, source: 'calendar_events_plus_one_event_dry_run_reports', calendar_fingerprint: 'calendar-fp', generated_fingerprint: 'week-fp', read_only: true },
  validation_warnings: ['Week preflight is read-only; no entries, draws, matches, points, or ranking snapshots are mutated.'],
  validation_errors: []
}

const weekRunResult = {
  preflight: weekPreflightResult,
  events: [{
    event_id: 'EVT-2000-W01-wt_a',
    event_name: 'World A',
    season_week: 1,
    calendar_year: 2000,
    year_week: 37,
    run_order: 1,
    preflight_stop_reason: null,
    initial_stage: 'planned',
    final_stage: 'points_generated',
    event_report: simulateOneEventResult.report,
    succeeded: true,
    blocked: false,
    changed_artifacts: simulateOneEventResult.report.changed_artifacts,
    warnings: ['run event warning'],
    errors: []
  }],
  summary: {
    season: '2000/2001', season_week: 1, calendar_year: 2000, year_week: 37, event_count: 1, attempted_event_count: 1, succeeded_event_count: 1, blocked_event_count: 0, failed_event_count: 0, points_applied_event_count: 0, snapshot_published: false, snapshot_skipped: false, snapshot_already_existed: false, can_run_preflight: true, run_started: true, run_completed: true, stopped_early: false, first_failed_event_id: null, stop_reason: null, next_safe_action: 'rerun_week_with_apply_points_when_ready'
  },
  metadata: { season: '2000/2001', season_week: 1, source: 'week_preflight_plus_one_event_execution_reports', preflight_fingerprint: 'week-fp', final_fingerprint: 'run-fp', read_only: false },
  validation_warnings: ['Week execution is mutating and no rollback is implemented; partial week runs must be inspected and rerun manually after resolving blockers.'],
  validation_errors: []
}


const weekRecoveryResult = {
  season: '2000/2001',
  season_week: 1,
  events: [{
    event_id: 'EVT-2000-W01-wt_a',
    event_name: 'World A',
    season: '2000/2001',
    season_week: 1,
    calendar_year: 2000,
    year_week: 37,
    category: 'PLATINUM',
    tour_level: 'WORLD_TOUR',
    host_country: 'ENG',
    current_stage: 'points_generated',
    next_recommended_action: 'apply_point_awards',
    is_blocked: false,
    block_reasons: [],
    entries_exists: true,
    draw_exists: true,
    matches_exists: true,
    results_exists: true,
    point_awards_exists: true,
    points_applied: false,
    ranking_snapshot_exists: false,
    safe_to_rerun_event: true,
    duplicate_points_risk: false,
    overwrite_risk: true,
    needs_manual_attention: false,
    recommended_event_action: 'apply_point_awards',
    recommended_rerun_flags: { overwrite_existing: false, apply_points: true, publish_snapshot: false, allow_blocked: false, allow_incomplete_results: false },
    warnings: ['Existing persisted artifacts are present; recovery recommends overwrite_existing=false.'],
    errors: []
  }],
  summary: {
    season: '2000/2001', season_week: 1, calendar_year: 2000, year_week: 37,
    event_count: 1, completed_event_count: 0, partial_event_count: 1, blocked_event_count: 0,
    points_generated_count: 1, points_applied_count: 0, snapshot_exists: false,
    week_complete: false, week_partial: true, week_blocked: false,
    ready_for_point_application: true, ready_for_snapshot_publication: false,
    duplicate_points_risk_count: 0, overwrite_risk_count: 1, manual_attention_count: 0,
    next_safe_action: 'rerun_week_with_apply_points',
    recommended_week_rerun_flags: { overwrite_existing: false, apply_points: true, publish_snapshot: false, allow_blocked: false, allow_incomplete_results: false },
    rollback_available: false
  },
  metadata: { season: '2000/2001', season_week: 1, source: 'persisted_artifact_recovery_read_model', generated_fingerprint: 'recovery-fp', read_only: true },
  validation_warnings: ['Recovery diagnostics are read-only. No rollback, deletion, reversal, or overwrite is performed.'],
  validation_errors: []
}


const seasonReadinessResult = {
  season: '2000/2001',
  weeks: [
    { season: '2000/2001', season_week: 1, calendar_year: 2000, year_week: 37, event_count: 1, has_events: true, status: 'ready_for_point_application', week_complete: false, week_partial: true, week_blocked: false, ready_for_point_application: true, ready_for_snapshot_publication: false, snapshot_exists: false, completed_event_count: 0, partial_event_count: 1, blocked_event_count: 0, points_generated_count: 1, points_applied_count: 0, duplicate_points_risk_count: 0, overwrite_risk_count: 1, manual_attention_count: 0, next_safe_action: 'apply_points', recommended_week_rerun_flags: { overwrite_existing: false, apply_points: true, publish_snapshot: false, allow_blocked: false, allow_incomplete_results: false }, representative_event_ids: ['EVT-2000-W01-wt_a'], warnings: ['readiness warning'], errors: [], recovery_fingerprint: 'recovery-fp' },
    { season: '2000/2001', season_week: 2, calendar_year: 2000, year_week: 38, event_count: 0, has_events: false, status: 'empty', week_complete: false, week_partial: false, week_blocked: false, ready_for_point_application: false, ready_for_snapshot_publication: false, snapshot_exists: false, completed_event_count: 0, partial_event_count: 0, blocked_event_count: 0, points_generated_count: 0, points_applied_count: 0, duplicate_points_risk_count: 0, overwrite_risk_count: 0, manual_attention_count: 0, next_safe_action: 'no_events', recommended_week_rerun_flags: { overwrite_existing: false, apply_points: false, publish_snapshot: false, allow_blocked: false, allow_incomplete_results: false }, representative_event_ids: [], warnings: [], errors: [], recovery_fingerprint: 'empty-fp' }
  ],
  summary: { season: '2000/2001', total_weeks: 61, weeks_with_events: 1, empty_weeks: 60, complete_weeks: 0, partial_weeks: 0, blocked_weeks: 0, ready_for_point_application_weeks: 1, ready_for_snapshot_publication_weeks: 0, weeks_missing_snapshot_after_points: 0, total_events: 1, total_blocked_events: 0, total_manual_attention_count: 0, first_incomplete_week: 1, first_blocked_week: null, next_week_to_run: 1, season_ready_to_continue: true, season_complete: false, next_safe_action: 'apply_points' },
  metadata: { season: '2000/2001', source: 'season_week_recovery_aggregation', generated_fingerprint: 'season-readiness-fp', read_only: true },
  validation_warnings: ['Season readiness is read-only. It aggregates week recovery reports and does not run events, apply points, or publish snapshots.'],
  validation_errors: []
}


const seasonRangePreflightResult = {
  season: '2000/2001',
  start_week: 1,
  end_week: 2,
  weeks: [
    { season: '2000/2001', season_week: 1, calendar_year: 2000, year_week: 37, status: 'planned', event_count: 1, has_events: true, week_complete: false, week_blocked: false, week_partial: false, ready_for_point_application: false, ready_for_snapshot_publication: false, snapshot_exists: false, next_safe_action: 'run_week', recommended_week_rerun_flags: { overwrite_existing: false, apply_points: true, publish_snapshot: true, allow_blocked: false, allow_incomplete_results: false }, range_action: 'run_week', would_mutate_if_executed: true, would_apply_points_if_executed: true, would_publish_snapshot_if_executed: true, warnings: [], errors: [] },
    { season: '2000/2001', season_week: 2, calendar_year: 2000, year_week: 38, status: 'complete', event_count: 1, has_events: true, week_complete: true, week_blocked: false, week_partial: false, ready_for_point_application: false, ready_for_snapshot_publication: false, snapshot_exists: true, next_safe_action: 'review_completed_season', recommended_week_rerun_flags: { overwrite_existing: false, apply_points: false, publish_snapshot: false, allow_blocked: false, allow_incomplete_results: false }, range_action: 'skip_complete', would_mutate_if_executed: false, would_apply_points_if_executed: false, would_publish_snapshot_if_executed: false, warnings: ['range warning'], errors: [] }
  ],
  summary: { season: '2000/2001', start_week: 1, end_week: 2, total_weeks_in_range: 2, empty_weeks: 0, completed_weeks: 1, runnable_weeks: 1, point_application_weeks: 0, snapshot_publication_weeks: 0, blocked_weeks: 0, recoverable_weeks: 0, skipped_weeks: 1, first_unsafe_week: null, first_blocked_week: null, first_runnable_week: 1, range_safe_to_run: true, would_apply_points: true, would_publish_snapshots: true, next_safe_action: 'run_range', recommended_run_flags: { overwrite_existing: false, apply_points: true, publish_snapshot: true, allow_blocked: false, allow_incomplete_results: false }, mutation_warning: 'Range preflight is read-only. It plans a future range run but does not run weeks, apply points, or publish snapshots.' },
  metadata: { season: '2000/2001', source: 'season_readiness_range_preflight', season_readiness_fingerprint: 'season-readiness-fp', generated_fingerprint: 'range-preflight-fp', read_only: true },
  validation_warnings: ['Range preflight is read-only. It plans a future range run but does not run weeks, apply points, or publish snapshots.'],
  validation_errors: []
}


const seasonRangeRunResult = {
  preflight: seasonRangePreflightResult,
  weeks: [
    { season_week: 1, calendar_year: 2000, year_week: 37, status_before: 'planned', range_action: 'run_week', run_order: 1, skipped: false, skip_reason: null, week_run_result: weekRunResult, succeeded: true, blocked: false, failed: false, warnings: [], errors: [] },
    { season_week: 2, calendar_year: 2000, year_week: 38, status_before: 'complete', range_action: 'skip_complete', run_order: null, skipped: true, skip_reason: 'completed_week', week_run_result: null, succeeded: true, blocked: false, failed: false, warnings: ['range warning'], errors: [] }
  ],
  summary: { season: '2000/2001', start_week: 1, end_week: 2, attempted_week_count: 2, skipped_empty_week_count: 0, skipped_complete_week_count: 1, executed_week_count: 1, succeeded_week_count: 1, blocked_week_count: 0, failed_week_count: 0, point_application_week_count: 1, snapshot_publication_week_count: 1, run_started: true, run_completed: true, stopped_early: false, first_failed_week: null, first_blocked_week: null, stop_reason: null, next_safe_action: 'review_completed_range', no_rollback_warning: 'Range execution is mutating and no rollback is implemented; earlier successful weeks remain persisted if a later week blocks or fails.', range_safe_to_run_preflight: true },
  metadata: { season: '2000/2001', source: 'range_preflight_plus_week_execution_reports', range_preflight_fingerprint: 'range-preflight-fp', final_fingerprint: 'range-run-fp', read_only: false },
  validation_warnings: ['Range execution is mutating and no rollback is implemented; earlier successful weeks remain persisted if a later week blocks or fails.'],
  validation_errors: []
}

const unsafeWeekRunResult = {
  ...weekRunResult,
  events: [],
  summary: { ...weekRunResult.summary, attempted_event_count: 0, succeeded_event_count: 0, run_started: false, run_completed: false, stop_reason: 'preflight_not_safe', next_safe_action: 'resolve_preflight_blocker' },
  validation_errors: ['publish_snapshot=true requires apply_points=true for week preflight.']
}

const pointAwardsResult = {
  award_package: {
    event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', template_id: 'wt_a', event_name: 'World A', category: 'PLATINUM', tour_level: 'WORLD_TOUR', seed: 12345, dry_run: true, persisted: false, applied: false,
    awards: [
      { player_id: 'P-2000-AAA-0001', player_name: 'Adam Ahmed AA01', country_code: 'AAA', reached_stage: 'champion', qualifier: false, seed_number: 1, ranking_points_awarded: 1000, race_points_awarded: 1000, previous_ranking_points: 0, previous_race_points: 0, projected_ranking_points: 1000, projected_race_points: 1000, source_result_fingerprint: 'result-build-fp', source_player_result_fingerprint: 'player-result-fp-a', award_fingerprint: 'award-fp-a' },
      { player_id: 'P-2000-BBB-0002', player_name: 'Ben Beta BB02', country_code: 'BBB', reached_stage: 'finalist', qualifier: true, seed_number: null, ranking_points_awarded: 650, race_points_awarded: 650, previous_ranking_points: 0, previous_race_points: 0, projected_ranking_points: 650, projected_race_points: 650, source_result_fingerprint: 'result-build-fp', source_player_result_fingerprint: 'player-result-fp-b', award_fingerprint: 'award-fp-b' }
    ],
    summary: { event_id: 'EVT-2000-W01-wt_a', player_count: 2, awarded_player_count: 2, total_ranking_points: 1650, total_race_points: 1650, champion_player_id: 'P-2000-AAA-0001', champion_points: 1000, finalist_player_id: 'P-2000-BBB-0002', finalist_points: 650, applied: false, validation_warning_count: 1, validation_error_count: 1 },
    metadata: { event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', seed: 12345, dry_run: true, persisted: false, applied: false, build_fingerprint: 'points-build-fp', result_package_fingerprint: 'result-build-fp', point_distribution_fingerprint: 'dist-fp', point_distribution_source: 'fallback.default_stage_points', ranking_updates_implemented: true, rolling_ranking_implemented: false, best_n_implemented: false, persistence_path: null },
    validation_warnings: [{ severity: 'warning', code: 'point_warn', message: 'point warning', event_id: 'EVT-2000-W01-wt_a', match_id: null, player_id: null, field: null }],
    validation_errors: [{ severity: 'error', code: 'point_error', message: 'point error', event_id: 'EVT-2000-W01-wt_a', match_id: null, player_id: 'P-2000-BBB-0002', field: null }]
  },
  summary: { event_id: 'EVT-2000-W01-wt_a', player_count: 2, awarded_player_count: 2, total_ranking_points: 1650, total_race_points: 1650, champion_player_id: 'P-2000-AAA-0001', champion_points: 1000, finalist_player_id: 'P-2000-BBB-0002', finalist_points: 650, applied: false, validation_warning_count: 1, validation_error_count: 1 },
  metadata: { event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', seed: 12345, dry_run: true, persisted: false, applied: false, build_fingerprint: 'points-build-fp', result_package_fingerprint: 'result-build-fp', point_distribution_fingerprint: 'dist-fp', point_distribution_source: 'fallback.default_stage_points', ranking_updates_implemented: true, rolling_ranking_implemented: false, best_n_implemented: false, persistence_path: null },
  validation_warnings: [{ severity: 'warning', code: 'point_warn', message: 'point warning', event_id: 'EVT-2000-W01-wt_a', match_id: null, player_id: null, field: null }],
  validation_errors: [{ severity: 'error', code: 'point_error', message: 'point error', event_id: 'EVT-2000-W01-wt_a', match_id: null, player_id: 'P-2000-BBB-0002', field: null }],
  award_package_exists: false,
  applied: false
}

const persistedPointAwardsResult = {
  ...pointAwardsResult,
  award_package: { ...pointAwardsResult.award_package, dry_run: false, persisted: true, metadata: { ...pointAwardsResult.award_package.metadata, dry_run: false, persisted: true } },
  metadata: { ...pointAwardsResult.metadata, dry_run: false, persisted: true },
  award_package_exists: true
}

const pointApplyResult = {
  event_id: 'EVT-2000-W01-wt_a',
  applied: true,
  award_package: { ...persistedPointAwardsResult.award_package, applied: true, summary: { ...persistedPointAwardsResult.award_package.summary, applied: true }, metadata: { ...persistedPointAwardsResult.award_package.metadata, applied: true } },
  updated_players: [{ player_id: 'P-2000-AAA-0001', player_name: 'Adam Ahmed AA01', previous_ranking_points: 0, previous_race_points: 0, new_ranking_points: 1000, new_race_points: 1000, delta_ranking_points: 1000, delta_race_points: 1000 }],
  validation_warnings: [],
  validation_errors: [],
  metadata: { ...persistedPointAwardsResult.metadata, applied: true }
}

const emptyPointAwardsResult = { award_package: null, summary: null, metadata: null, validation_warnings: [], validation_errors: [], award_package_exists: false, applied: false }

const rankingTableResponse = {
  rows: [{ rank: 1, dense_rank: 1, ordinal_position: 1, player_id: 'P-2000-AAA-0001', player_name: 'Adam Ahmed AA01', country_code: 'AAA', nationality: 'AAA', age_years_at_season_start: 24, career_stage: 'prime', current_ability: 78, potential_ability: 88, potential_tier: 'A', archetype: 'all_court', play_style: 'balanced', ranking_points: 1000, race_points: 900, table_points: 1000, manual_override: false, source_generation: 'initial_pool', locked_from_initial_pool: true, movement: null, previous_rank: null, events_counted: null, player_fingerprint: 'source-fp' }],
  summary: { season: '2000/2001', table_type: 'ranking', player_count: 1, total_source_players: 1, ranked_player_count: 1, zero_point_players: 0, countries_represented: 1, leader_player_id: 'P-2000-AAA-0001', leader_points: 1000, generated_from_active_players_fingerprint: 'active-fp', rolling_ranking_implemented: false, best_n_implemented: false, movement_implemented: false },
  metadata: { season: '2000/2001', table_type: 'ranking', source: 'season_active_players', active_players_fingerprint: 'active-fp', generated_fingerprint: 'ranking-fp', ranking_basis: 'current active season player ranking_points', filters: { country_code: null, search: null, include_zero_points: true, min_points: null }, limit: 100, warnings: ['Rolling 61-week ranking not implemented.'] },
  validation_warnings: ['Rolling 61-week ranking not implemented.', 'Best-N ranking selection not implemented.'],
  validation_errors: []
}

async function expandAdminSection(name: RegExp | string): Promise<void> {
  const sectionButton = await screen.findByRole('button', { name })
  if (sectionButton.getAttribute('aria-expanded') !== 'true') {
    await userEvent.click(sectionButton)
  }
}

describe('AdminSeasonsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSeasonActivePlayers.mockResolvedValue(empty)
    api.getSeasonRegistry.mockResolvedValue({
      start_season: '2000/01',
      end_season: '2039/40',
      season_count: 40,
      week_count: 61,
      season_week_1_year_week: 37,
      seasons: [{ label: '2000/01', season_start_year: 2000, season_index: 0, week_count: 61, season_week_start: 1, season_week_end: 61, year_week_start: 37, year_week_end: 36, status: 'registry_only' }]
    })
    api.getAdminRankingTable.mockResolvedValue(rankingTableResponse)
    api.getViewerRankingTable.mockResolvedValue(rankingTableResponse)
    api.getAdminRankingSnapshot.mockResolvedValue({ snapshot: null, snapshot_exists: false, summary: { ranking: { table_type: 'ranking', row_count: 0, include_zero_points: true, generated_at: '2000-01-01T00:00:00Z' }, race: { table_type: 'race', row_count: 0, include_zero_points: true, generated_at: '2000-01-01T00:00:00Z' } }, metadata: null, validation_warnings: [], validation_errors: [] })
    api.getAdminPointBreakdown.mockResolvedValue({ breakdown: null, summary_rows: [{ player_id: 'P-1' }], metadata: { season: '2000/01' }, validation_warnings: [], validation_errors: [] })
    api.bootstrapSeasonFromInitialPool.mockResolvedValue(response)
    api.getSeasonCalendar.mockResolvedValue(emptyCalendar)
    api.buildSeasonCalendar.mockResolvedValue(calendarResponse)
    api.getSeasonLifecycle.mockResolvedValue(lifecycleResponse)
    api.getEventEntryList.mockResolvedValue(emptyEntryResult)
    api.generateEventEntryList.mockResolvedValue(entryResult)
    api.getEventDrawPackage.mockResolvedValue(emptyDrawResult)
    api.generateEventDrawPackage.mockResolvedValue(drawResult)
    api.getEventMatchPackage.mockResolvedValue(emptyMatchResult)
    api.generateEventMatchPackage.mockResolvedValue(matchResult)
    api.simulateNextEventMatch.mockResolvedValue(simulatedMatchResult)
    api.simulateEventMatch.mockResolvedValue(simulatedMatchResult)
    api.getEventProgressionStatus.mockResolvedValue(progressionStatus)
    api.processEventByes.mockResolvedValue({ ...progressionResult, action: 'process_byes' })
    api.refreshEventProgression.mockResolvedValue({ ...progressionResult, action: 'advance_completed' })
    api.promoteEventQualifiers.mockResolvedValue({ ...progressionResult, action: 'promote_qualifiers' })
    api.simulateEventRound.mockResolvedValue(progressionResult)
    api.simulateEventDraw.mockResolvedValue({ ...progressionResult, action: 'simulate_draw' })
    api.getEventResultPackage.mockResolvedValue(emptyEventResult)
    api.extractEventResultPackage.mockResolvedValue(eventResult)
    api.getEventPointAwards.mockResolvedValue(emptyPointAwardsResult)
    api.generateEventPointAwards.mockResolvedValue(pointAwardsResult)
    api.applyEventPointAwards.mockResolvedValue(pointApplyResult)
    api.simulateOneEvent.mockResolvedValue(simulateOneEventResult)
    api.preflightSeasonWeek.mockResolvedValue(weekPreflightResult)
    api.runSeasonWeek.mockResolvedValue(weekRunResult)
    api.recoverSeasonWeek.mockResolvedValue(weekRecoveryResult)
    api.getSeasonReadiness.mockResolvedValue(seasonReadinessResult)
  })


  it('renders workflow banner and open primary workflow sections', async () => {
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')

    expect(await screen.findByLabelText('Recommended Phase 1 workflow')).toBeInTheDocument()
    expect(screen.getByText('Range 1–61 is effectively a full season run, but safer and more inspectable.')).toBeInTheDocument()
    expect(screen.getByText('Mutating commands are explicitly marked.')).toBeInTheDocument()
    expect(screen.getByText('No rollback is implemented.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Season Control Overview/i })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: /Primary Workflow/i })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('heading', { name: 'Season Calendar Builder' })).toBeInTheDocument()
  })

  it('renders selected season workspace for valid season labels', async () => {
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons?season=2000%2F01')
    expect(await screen.findByRole('heading', { name: 'Selected Season Workspace' })).toBeInTheDocument()
    await waitFor(() => expect(api.getSeasonRegistry).toHaveBeenCalled())
    expect(screen.getByText(/Compact label/)).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes('Compact label: 2000/01'))).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes('Legacy label: 2000/2001'))).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Registry Metadata' })).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes('Start year: 2000'))).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes('Season week range: SW1–SW61'))).toBeInTheDocument()
    expect(screen.getByText('Operational Read-only Preview')).toBeInTheDocument()
    expect(screen.getByText('Ranking snapshot W1')).toBeInTheDocument()
    expect(screen.getByText('Point breakdowns')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Calendar Validation' })).toHaveAttribute('href', '/admin/tour-seasons/validation')
    expect(screen.getByRole('link', { name: 'Open concrete season detail' })).toHaveAttribute('href', '/admin/seasons/detail/2000%2F01')
    const workspace = screen.getByRole('heading', { name: 'Selected Season Workspace' }).closest('article')
    expect(workspace).not.toBeNull()
    if (workspace) {
      expect(within(workspace).queryByRole('button', { name: /persist/i })).not.toBeInTheDocument()
      expect(within(workspace).queryByRole('button', { name: /preview/i })).not.toBeInTheDocument()
      expect(within(workspace).queryByRole('button', { name: /apply/i })).not.toBeInTheDocument()
    }
  })

  it('shows invalid selected season warning without crashing', async () => {
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons?season=bad-label')
    expect(await screen.findByText('Selected season label is invalid.')).toBeInTheDocument()
    expect(screen.getByText(/Raw label/)).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes('Raw label: bad-label'))).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Registry Metadata' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /build from template/i })).not.toBeInTheDocument()
  })

  it('shows valid-but-missing-registry warning without fake metadata', async () => {
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons?season=1999%2F00')
    expect(await screen.findByRole('heading', { name: 'Selected Season Workspace' })).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes('Compact label: 1999/00'))).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes('Legacy label: 1999/2000'))).toBeInTheDocument()
    expect(screen.getByText('This season label is valid but not present in the fixed registry.')).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes('Unavailable (valid label not in fixed registry)'))).toBeInTheDocument()
    expect(screen.queryByText('registry_only')).not.toBeInTheDocument()
  })

  it('does not show mutation-style actions inside selected season workspace', async () => {
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons?season=2000%2F01')
    const workspaceHeading = await screen.findByRole('heading', { name: 'Selected Season Workspace' })
    const workspace = workspaceHeading.closest('article')
    expect(workspace).not.toBeNull()
    if (!workspace) return
    const workspaceScope = within(workspace)
    expect(workspaceScope.queryByRole('button', { name: /build/i })).not.toBeInTheDocument()
    expect(workspaceScope.queryByRole('button', { name: /generate/i })).not.toBeInTheDocument()
    expect(workspaceScope.queryByRole('button', { name: /bootstrap/i })).not.toBeInTheDocument()
    expect(workspaceScope.queryByRole('button', { name: /apply/i })).not.toBeInTheDocument()
    expect(workspaceScope.queryByRole('button', { name: /simulate/i })).not.toBeInTheDocument()
  })

  it('renders advanced sections collapsed and keeps manual controls accessible after expansion', async () => {
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')

    expect(await screen.findByRole('button', { name: /Manual Artifact Tools \/ Advanced/i })).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByRole('button', { name: /Event-Level Tools/i })).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByRole('button', { name: /Rankings \/ Snapshots/i })).toHaveAttribute('aria-expanded', 'false')

    await expandAdminSection(/Manual Artifact Tools \/ Advanced/i)
    expect(screen.getByRole('heading', { name: 'Event Entries' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Preview entries' })).toBeInTheDocument()
  })

  it('shows read-only and mutating badges on workflow warnings', async () => {
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')

    expect(await screen.findAllByText('READ-ONLY')).not.toHaveLength(0)
    expect(screen.getByText(/Range preflight is read-only/)).toBeInTheDocument()
    expect(screen.getAllByText('MUTATING').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/No rollback is implemented/).length).toBeGreaterThan(0)
  })

  it('renders bootstrap controls and previews with dry_run true', async () => {
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')

    expect(await screen.findByRole('heading', { name: 'Seasons / Bootstrap' })).toBeInTheDocument()
    expect(screen.getAllByLabelText('Target season')[0]).toHaveValue('2000/2001')
    expect(screen.getByLabelText('Source initial pool season')).toHaveValue('2000/2001')
    expect(screen.getAllByLabelText('Seed')[0]).toHaveValue(12345)

    await userEvent.click(screen.getByRole('button', { name: 'Preview bootstrap' }))
    expect(api.bootstrapSeasonFromInitialPool).toHaveBeenCalledWith('2000/2001', expect.objectContaining({ dry_run: true, seed: 12345 }))
    expect(await screen.findByText('Source initial pool is very small for a professional tour bootstrap.')).toBeInTheDocument()
  })

  it('persists with dry_run false and renders active player table', async () => {
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Rankings \/ Snapshots/i)

    await userEvent.click(await screen.findByRole('button', { name: 'Persist bootstrap' }))
    expect(api.bootstrapSeasonFromInitialPool).toHaveBeenCalledWith('2000/2001', expect.objectContaining({ dry_run: false }))

    const table = await screen.findByRole('table', { name: 'Active season players table' })
    expect(within(table).getByText('Adam Ahmed AA01')).toBeInTheDocument()
    expect(within(table).getByText('fresh')).toBeInTheDocument()
    expect(within(table).getAllByText('0').length).toBeGreaterThan(0)
  })

  it('renders calendar builder controls and previews calendar', async () => {
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')

    expect(await screen.findByRole('heading', { name: 'Season Calendar Builder' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Preview calendar' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Preview calendar' }))
    expect(api.buildSeasonCalendar).toHaveBeenCalledWith('2000/2001', expect.objectContaining({ dry_run: true, seed: 12345 }))
    const table = await screen.findByRole('table', { name: 'Season calendar events table' })
    expect(within(table).getByText('World A')).toBeInTheDocument()
    expect(screen.getByText('ranking_race_not_integrated: ranking/race integration not implemented yet')).toBeInTheDocument()
    expect(screen.getByText('example_error: example error')).toBeInTheDocument()
  })

  it('persists calendar with dry_run false', async () => {
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')

    await userEvent.click(await screen.findByRole('button', { name: 'Persist calendar' }))
    expect(api.buildSeasonCalendar).toHaveBeenCalledWith('2000/2001', expect.objectContaining({ dry_run: false }))
  })

  it('renders Event Lifecycle section and loads read-only lifecycle status', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Event-Level Tools/i)

    expect(await screen.findByRole('heading', { name: 'Event Lifecycle' })).toBeInTheDocument()
    expect(screen.getByText('Lifecycle is a read-only status derived from persisted event artifacts. It does not generate entries, simulate matches, apply points, or publish rankings.')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Load lifecycle' }))
    expect(api.getSeasonLifecycle).toHaveBeenCalledWith('2000/2001')
    const table = await screen.findByRole('table', { name: 'Event lifecycle table' })
    expect(within(table).getByText('entries_generated')).toBeInTheDocument()
    expect(within(table).getByText('generate_draw')).toBeInTheDocument()
    expect(within(table).getByText('blocked')).toBeInTheDocument()
    expect(screen.getByText('entries artifact has 1 validation error(s)')).toBeInTheDocument()
  })



  it('renders Simulate One Event panel and previews through API', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Event-Level Tools/i)

    expect(await screen.findByRole('heading', { name: 'Simulate One Event' })).toBeInTheDocument()
    expect(screen.getByText('This command orchestrates existing backend services for one event. It does not simulate a full week or full season. Applying points and publishing snapshots are opt-in.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Preview event simulation' }))
    expect(api.simulateOneEvent).toHaveBeenCalledWith('EVT-2000-W01-wt_a', expect.objectContaining({ dry_run: true, apply_points: false, publish_snapshot: false, simulate_draw_type: 'qualification_then_main' }))
    expect(screen.getByText('Point application mutates active season players. Snapshot publication mutates weekly ranking snapshot registry. Dry-run is plan-only.')).toBeInTheDocument()
    expect(screen.getAllByText('Stop reason').length).toBeGreaterThan(0)
    expect(screen.getByText('dry_run_plan_only')).toBeInTheDocument()
    expect(screen.getByText('Safe to rerun')).toBeInTheDocument()
    const artifactTable = await screen.findByRole('table', { name: 'Simulate one event artifact state table' })
    expect(within(artifactTable).getByText('Point awards')).toBeInTheDocument()
    const table = await screen.findByRole('table', { name: 'Simulate one event steps table' })
    expect(within(table).getByText('generate_entries')).toBeInTheDocument()
    expect(within(table).getByText('planned')).toBeInTheDocument()
    expect(within(table).getByText('SeasonPointAwardsService.generate_event_point_awards')).toBeInTheDocument()
    expect(within(table).getByText('777')).toBeInTheDocument()
    expect(screen.getByText('report warning')).toBeInTheDocument()
    expect(screen.getByText('report error')).toBeInTheDocument()
    expect(within(table).getByText('sim warning')).toBeInTheDocument()
    expect(within(table).getByText('sim error')).toBeInTheDocument()
  })

  it('runs Simulate One Event with dry_run false and opt-in flags', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Event-Level Tools/i)

    await userEvent.click(await screen.findByLabelText('Apply points'))
    await userEvent.click(screen.getByLabelText('Publish ranking snapshot'))
    await userEvent.selectOptions(screen.getByLabelText('Simulate draw type'), 'main')
    await userEvent.click(screen.getByRole('button', { name: 'Run event simulation' }))
    expect(api.simulateOneEvent).toHaveBeenCalledWith('EVT-2000-W01-wt_a', expect.objectContaining({ dry_run: false, apply_points: true, publish_snapshot: true, simulate_draw_type: 'main' }))
    expect(await screen.findByText('points_generated')).toBeInTheDocument()
  })



  it('renders Season Simulation Readiness, calls API, displays summary and table, and sends filters', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')

    expect(await screen.findByRole('heading', { name: 'Season Simulation Readiness' })).toBeInTheDocument()
    expect(screen.getByText('Season readiness is read-only. It aggregates week recovery reports and does not run events, apply points, or publish snapshots.')).toBeInTheDocument()
    await userEvent.clear(screen.getByLabelText('Readiness event ID filter'))
    await userEvent.type(screen.getByLabelText('Readiness event ID filter'), 'EVT-2000-W01-wt_a')
    await userEvent.click(screen.getByLabelText('Include empty weeks'))
    await userEvent.click(screen.getByLabelText('Include completed weeks'))
    await userEvent.click(screen.getByRole('button', { name: 'Inspect season readiness' }))

    expect(api.getSeasonReadiness).toHaveBeenCalledWith({ season: '2000/2001', include_empty_weeks: false, include_completed_weeks: false, event_id_filter: ['EVT-2000-W01-wt_a'] })
    expect(await screen.findByText('Season readiness summary')).toBeInTheDocument()
    expect(screen.getByText('Total weeks')).toBeInTheDocument()
    expect(screen.getByText('Next week to run')).toBeInTheDocument()
    expect(screen.getAllByText('apply_points').length).toBeGreaterThan(0)
    const table = await screen.findByRole('table', { name: 'Season readiness weeks table' })
    expect(within(table).getByText('ready_for_point_application')).toBeInTheDocument()
    expect(within(table).getByText('1/0')).toBeInTheDocument()
    expect(screen.getByText('Selected week detail')).toBeInTheDocument()
    expect(screen.getAllByText('EVT-2000-W01-wt_a').length).toBeGreaterThan(0)
    expect(screen.getByText('readiness warning')).toBeInTheDocument()
  })


  it('renders Season Range Preflight, calls API, displays summary, flags, warning, and week actions', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    api.preflightSeasonRange.mockResolvedValue(seasonRangePreflightResult)
    api.runSeasonRange.mockResolvedValue(seasonRangeRunResult)
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')

    expect(await screen.findByRole('heading', { name: 'Season Range Preflight' })).toBeInTheDocument()
    expect(screen.getByText('Range preflight is read-only. It plans a future range run but does not run weeks, apply points, or publish snapshots.')).toBeInTheDocument()
    await userEvent.clear(screen.getByLabelText('Start week'))
    await userEvent.type(screen.getByLabelText('Start week'), '1')
    await userEvent.clear(screen.getByLabelText('End week'))
    await userEvent.type(screen.getByLabelText('End week'), '2')
    await userEvent.clear(screen.getByLabelText('Range event ID filter'))
    await userEvent.type(screen.getByLabelText('Range event ID filter'), 'EVT-2000-W01-wt_a')
    await userEvent.click(screen.getByRole('button', { name: 'Preview range' }))

    expect(api.preflightSeasonRange).toHaveBeenCalledWith({ season: '2000/2001', start_week: 1, end_week: 2, apply_points: true, publish_snapshot: true, include_empty_weeks: true, include_completed_weeks: true, stop_on_blocked: true, event_id_filter: ['EVT-2000-W01-wt_a'] })
    expect(await screen.findByText('Season range preflight summary')).toBeInTheDocument()
    expect(screen.getByText('Range safe to run')).toBeInTheDocument()
    expect(screen.getByText('Recommended future run flags')).toBeInTheDocument()
    expect(screen.getByText('allow_incomplete_results')).toBeInTheDocument()
    const table = await screen.findByRole('table', { name: 'Season range preflight weeks table' })
    expect(within(table).getByText('run_week')).toBeInTheDocument()
    expect(within(table).getByText('skip_complete')).toBeInTheDocument()
    expect(within(table).getByText('range warning')).toBeInTheDocument()
  })


  it('renders Run Season Range, calls API, warns, and displays summary and week table', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    api.runSeasonRange.mockResolvedValue(seasonRangeRunResult)
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')

    expect(await screen.findByRole('heading', { name: 'Run Season Range' })).toBeInTheDocument()
    expect(screen.getByText('This is mutating. It may run multiple weeks, apply points, and publish weekly snapshots. No rollback is implemented.')).toBeInTheDocument()
    await userEvent.clear(screen.getByLabelText('Run start week'))
    await userEvent.type(screen.getByLabelText('Run start week'), '1')
    await userEvent.clear(screen.getByLabelText('Run end week'))
    await userEvent.type(screen.getByLabelText('Run end week'), '2')
    await userEvent.clear(screen.getByLabelText('Run event ID filter'))
    await userEvent.type(screen.getByLabelText('Run event ID filter'), 'EVT-2000-W01-wt_a')
    await userEvent.click(screen.getByRole('button', { name: 'Run range' }))

    expect(api.runSeasonRange).toHaveBeenCalledWith(expect.objectContaining({ season: '2000/2001', start_week: 1, end_week: 2, seed: 12345, apply_points: true, publish_snapshot: true, allow_unsafe_run: false, event_id_filter: ['EVT-2000-W01-wt_a'] }))
    expect(await screen.findByText('Season range run summary')).toBeInTheDocument()
    expect(screen.getByText('Executed weeks')).toBeInTheDocument()
    expect(screen.getByText('Skipped complete')).toBeInTheDocument()
    expect(screen.getByText('Next safe action')).toBeInTheDocument()
    const table = await screen.findByRole('table', { name: 'Season range run weeks table' })
    expect(within(table).getByText('run_week')).toBeInTheDocument()
    expect(within(table).getByText('completed_week')).toBeInTheDocument()
  })

  it('renders week preflight panel and previews through API', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Event-Level Tools/i)

    expect(await screen.findByRole('heading', { name: 'Simulate One Season Week — Preflight' })).toBeInTheDocument()
    expect(screen.getByText('This is preflight only. It calls one-event dry-run planning for each event and does not mutate entries, draws, matches, points, or snapshots.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Preview week simulation' }))
    expect(api.preflightSeasonWeek).toHaveBeenCalledWith(expect.objectContaining({ season: '2000/2001', season_week: 1, seed: 12345, apply_points: false, publish_snapshot: false, event_id_filter: [] }))
    expect(await screen.findByText('Week preflight summary')).toBeInTheDocument()
    expect(screen.getByText('Can run week')).toBeInTheDocument()
    expect(screen.getByText('Snapshot already exists')).toBeInTheDocument()
    const table = await screen.findByRole('table', { name: 'Season week preflight events table' })
    expect(within(table).getByText('World A')).toBeInTheDocument()
    expect(within(table).getByText('generate_entries')).toBeInTheDocument()
    expect(screen.getByText('Selected event dry-run detail')).toBeInTheDocument()
    expect(screen.getAllByText('dry_run_plan_only').length).toBeGreaterThan(0)
  })


  it('renders recovery panel, calls API, and displays backend recommendations', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Event-Level Tools/i)

    expect(await screen.findByRole('heading', { name: 'Week Run Recovery / Diagnostics' })).toBeInTheDocument()
    expect(screen.getByText('Recovery diagnostics are read-only. No rollback, deletion, reversal, or overwrite is performed.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Inspect week recovery' }))
    expect(api.recoverSeasonWeek).toHaveBeenCalledWith({ season: '2000/2001', season_week: 1, event_id_filter: [], include_completed_events: true })
    expect(await screen.findByText('Week recovery summary')).toBeInTheDocument()
    expect(screen.getByText('Week complete')).toBeInTheDocument()
    expect(screen.getByText('Ready for point application')).toBeInTheDocument()
    expect(screen.getByText('Recommended week rerun flags')).toBeInTheDocument()
    expect(screen.getAllByText('apply_points').length).toBeGreaterThan(0)
    const table = await screen.findByRole('table', { name: 'Week recovery events table' })
    expect(within(table).getByText('World A')).toBeInTheDocument()
    expect(within(table).getByText('points_generated')).toBeInTheDocument()
    expect(within(table).getByText('apply_point_awards')).toBeInTheDocument()
  })

  it('renders Run One Season Week panel and runs through API', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Event-Level Tools/i)

    expect(await screen.findByRole('heading', { name: 'Run One Season Week' })).toBeInTheDocument()
    expect(screen.getByText('This is mutating. It may create entries, draws, matches, results, point awards, apply points, and publish one weekly snapshot. No rollback is implemented.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Run week simulation' }))
    expect(api.runSeasonWeek).toHaveBeenCalledWith(expect.objectContaining({ season: '2000/2001', season_week: 1, seed: 12345, apply_points: false, publish_snapshot: false, allow_unsafe_run: false }))
    expect(await screen.findByText('Week run summary')).toBeInTheDocument()
    expect(screen.getByText('Run started')).toBeInTheDocument()
    expect(screen.getByText('Attempted events')).toBeInTheDocument()
    const table = await screen.findByRole('table', { name: 'Season week run events table' })
    expect(within(table).getByText('World A')).toBeInTheDocument()
    expect(screen.getByText('Preflight used for run')).toBeInTheDocument()
  })

  it('renders no-run state for unsafe week run response', async () => {
    api.runSeasonWeek.mockResolvedValue(unsafeWeekRunResult)
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Event-Level Tools/i)

    await userEvent.click(await screen.findByRole('button', { name: 'Run week simulation' }))
    expect(await screen.findByText('Preflight blocked execution, so no mutating event command was started.')).toBeInTheDocument()
    expect(screen.getByText('preflight_not_safe')).toBeInTheDocument()
    expect(screen.getByText('No event execution reports were produced.')).toBeInTheDocument()
  })

  it('renders Event Entries section and previews entries', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Manual Artifact Tools \/ Advanced/i)

    expect(await screen.findByRole('heading', { name: 'Event Entries' })).toBeInTheDocument()
    expect(screen.getByText('Entry generation selects players for a planned calendar event from active season players. It does not create draws or simulate matches yet.')).toBeInTheDocument()
    expect(await screen.findAllByText(/World A/)).not.toHaveLength(0)

    await userEvent.click(screen.getByRole('button', { name: 'Preview entries' }))
    expect(api.generateEventEntryList).toHaveBeenCalledWith('EVT-2000-W01-wt_a', expect.objectContaining({ dry_run: true, seed: 12345 }))
    const table = await screen.findByRole('table', { name: 'Event entries table' })
    expect(within(table).getByText('accepted_main_draw')).toBeInTheDocument()
    expect(within(table).getByText('Adam Ahmed AA01')).toBeInTheDocument()
    expect(screen.getByText('entry_error: entry error')).toBeInTheDocument()
    expect(screen.getByText('entry_warn: entry warning')).toBeInTheDocument()
  })

  it('persists entries with dry_run false', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Manual Artifact Tools \/ Advanced/i)

    await userEvent.click(await screen.findByRole('button', { name: 'Persist entries' }))
    expect(api.generateEventEntryList).toHaveBeenCalledWith('EVT-2000-W01-wt_a', expect.objectContaining({ dry_run: false }))
  })


  it('renders Event Draws section and previews draws', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    api.getEventEntryList.mockResolvedValue({ ...entryResult, entry_list_exists: true })
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Manual Artifact Tools \/ Advanced/i)

    expect(await screen.findByRole('heading', { name: 'Event Draws' })).toBeInTheDocument()
    expect(screen.getByText('Draw generation creates bracket slots from persisted entry lists. It does not simulate matches or update rankings yet.')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Preview draw' }))
    expect(api.generateEventDrawPackage).toHaveBeenCalledWith('EVT-2000-W01-wt_a', expect.objectContaining({ dry_run: true, seed: 12345 }))
    const mainTable = await screen.findByRole('table', { name: 'Main draw table' })
    expect(within(mainTable).getAllByText('Adam Ahmed AA01').length).toBeGreaterThan(0)
    expect(within(mainTable).getByText('Q placeholder')).toBeInTheDocument()
    const qualTable = await screen.findByRole('table', { name: 'Qualification draw table' })
    expect(within(qualTable).getAllByText('Ben Beta BB02').length).toBeGreaterThan(0)
    expect(screen.getByText('draw_error: draw error')).toBeInTheDocument()
    expect(screen.getByText('draw_warn: draw warning')).toBeInTheDocument()
  })

  it('persists draws with dry_run false', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    api.getEventEntryList.mockResolvedValue({ ...entryResult, entry_list_exists: true })
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Manual Artifact Tools \/ Advanced/i)

    await userEvent.click(await screen.findByRole('button', { name: 'Persist draw' }))
    expect(api.generateEventDrawPackage).toHaveBeenCalledWith('EVT-2000-W01-wt_a', expect.objectContaining({ dry_run: false }))
  })


  it('renders Event Matches section and previews match package', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    api.getEventEntryList.mockResolvedValue({ ...entryResult, entry_list_exists: true })
    api.getEventDrawPackage.mockResolvedValue({ ...drawResult, draw_package_exists: true })
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Manual Artifact Tools \/ Advanced/i)

    expect(await screen.findByRole('heading', { name: 'Event Matches' })).toBeInTheDocument()
    expect(screen.getByText('Match generation creates match records from persisted draw packages. Simulation stores results but does not update rankings/race yet.')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Preview match package' }))
    expect(api.generateEventMatchPackage).toHaveBeenCalledWith('EVT-2000-W01-wt_a', expect.objectContaining({ dry_run: true, seed: 12345 }))
    const table = await screen.findByRole('table', { name: 'Event matches table' })
    expect(within(table).getByText('Adam Ahmed AA01')).toBeInTheDocument()
    expect(within(table).getByText('Ben Beta BB02')).toBeInTheDocument()
    expect(screen.getByText('match_error: match error')).toBeInTheDocument()
    expect(screen.getByText('match_warn: match warning')).toBeInTheDocument()
  })

  it('persists match package with dry_run false', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    api.getEventEntryList.mockResolvedValue({ ...entryResult, entry_list_exists: true })
    api.getEventDrawPackage.mockResolvedValue({ ...drawResult, draw_package_exists: true })
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Manual Artifact Tools \/ Advanced/i)

    await userEvent.click(await screen.findByRole('button', { name: 'Persist match package' }))
    expect(api.generateEventMatchPackage).toHaveBeenCalledWith('EVT-2000-W01-wt_a', expect.objectContaining({ dry_run: false }))
  })

  it('renders progression status and calls progression command APIs', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    api.getEventEntryList.mockResolvedValue({ ...entryResult, entry_list_exists: true })
    api.getEventDrawPackage.mockResolvedValue({ ...drawResult, draw_package_exists: true })
    api.getEventMatchPackage.mockResolvedValue({ ...matchResult, match_package_exists: true })
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Manual Artifact Tools \/ Advanced/i)

    expect(await screen.findByRole('heading', { name: 'Progression status' })).toBeInTheDocument()
    expect(screen.getByText('Progression commands update match states and propagate winners. They do not update ranking/race yet.')).toBeInTheDocument()
    expect(screen.getAllByText('Adam Ahmed AA01').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Ben Beta BB02').length).toBeGreaterThan(0)

    await userEvent.click(screen.getByRole('button', { name: 'Refresh progression' }))
    expect(api.refreshEventProgression).toHaveBeenCalledWith('EVT-2000-W01-wt_a', { seed: 12345 })
    await userEvent.click(screen.getByRole('button', { name: 'Process BYEs' }))
    expect(api.processEventByes).toHaveBeenCalledWith('EVT-2000-W01-wt_a', { seed: 12345 })
    await userEvent.click(screen.getByRole('button', { name: 'Promote qualifiers' }))
    expect(api.promoteEventQualifiers).toHaveBeenCalledWith('EVT-2000-W01-wt_a', { seed: 12345 })
    await userEvent.selectOptions(screen.getByLabelText('Progression draw'), 'main')
    await userEvent.clear(screen.getByLabelText('Round number'))
    await userEvent.type(screen.getByLabelText('Round number'), '2')
    await userEvent.click(screen.getByRole('button', { name: 'Simulate round' }))
    expect(api.simulateEventRound).toHaveBeenCalledWith('EVT-2000-W01-wt_a', { seed: 12345, draw_type: 'main', round_number: 2 })
    expect(await screen.findByText(/Last progression action: simulate_round/)).toBeInTheDocument()
    expect(screen.getByText('progression_warn: progression warning')).toBeInTheDocument()
  })

  it('simulates next and selected match through API', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    api.getEventEntryList.mockResolvedValue({ ...entryResult, entry_list_exists: true })
    api.getEventDrawPackage.mockResolvedValue({ ...drawResult, draw_package_exists: true })
    api.getEventMatchPackage.mockResolvedValue({ ...matchResult, match_package_exists: true })
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Manual Artifact Tools \/ Advanced/i)

    await userEvent.click(await screen.findByRole('button', { name: 'Simulate next pending match' }))
    expect(api.simulateNextEventMatch).toHaveBeenCalledWith('EVT-2000-W01-wt_a', { seed: 12345 })
    expect(await screen.findByText('11-7, 11-8, 11-9')).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText('Selected match'), 'm1')
    await userEvent.click(screen.getByRole('button', { name: 'Simulate selected match' }))
    expect(api.simulateEventMatch).toHaveBeenCalledWith('EVT-2000-W01-wt_a', 'm1', { seed: 12345 })
  })


  it('renders Event Results section and previews extracted result package', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    api.getEventEntryList.mockResolvedValue({ ...entryResult, entry_list_exists: true })
    api.getEventDrawPackage.mockResolvedValue({ ...drawResult, draw_package_exists: true })
    api.getEventMatchPackage.mockResolvedValue({ ...simulatedMatchResult, match_package_exists: true })
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Manual Artifact Tools \/ Advanced/i)

    expect(await screen.findByRole('heading', { name: 'Event Results' })).toBeInTheDocument()
    expect(screen.getByText('Result extraction summarizes completed tournament outcomes. Point awards are generated and applied explicitly in the Ranking / Race Points section.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Preview results' }))
    expect(api.extractEventResultPackage).toHaveBeenCalledWith('EVT-2000-W01-wt_a', expect.objectContaining({ dry_run: true, seed: 12345 }))
    const topTable = await screen.findByRole('table', { name: 'Event result top finishers table' })
    expect(within(topTable).getByText('Champion')).toBeInTheDocument()
    expect(within(topTable).getByText('Adam Ahmed AA01')).toBeInTheDocument()
    const fullTable = await screen.findByRole('table', { name: 'Event full player results table' })
    expect(within(fullTable).getByText('champion')).toBeInTheDocument()
    expect(within(fullTable).getByText('finalist')).toBeInTheDocument()
    expect(screen.getByText('result_error: result error')).toBeInTheDocument()
    expect(screen.getByText('result_warn: result warning')).toBeInTheDocument()
  })

  it('persists extracted results with dry_run false', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    api.getEventEntryList.mockResolvedValue({ ...entryResult, entry_list_exists: true })
    api.getEventDrawPackage.mockResolvedValue({ ...drawResult, draw_package_exists: true })
    api.getEventMatchPackage.mockResolvedValue({ ...simulatedMatchResult, match_package_exists: true })
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Manual Artifact Tools \/ Advanced/i)

    await userEvent.click(await screen.findByRole('button', { name: 'Persist results' }))
    expect(api.extractEventResultPackage).toHaveBeenCalledWith('EVT-2000-W01-wt_a', expect.objectContaining({ dry_run: false }))
  })


  it('renders Event Points section and previews awards with dry_run true', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    api.getEventEntryList.mockResolvedValue({ ...entryResult, entry_list_exists: true })
    api.getEventDrawPackage.mockResolvedValue({ ...drawResult, draw_package_exists: true })
    api.getEventMatchPackage.mockResolvedValue({ ...simulatedMatchResult, match_package_exists: true })
    api.getEventResultPackage.mockResolvedValue({ ...eventResult, result_package_exists: true })
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Manual Artifact Tools \/ Advanced/i)

    expect(await screen.findByRole('heading', { name: 'Ranking / Race Points' })).toBeInTheDocument()
    expect(screen.getByText('Point awarding uses persisted event results. Applying points mutates active season player ranking/race points. Rolling 61-week ranking and best-N logic are not implemented yet.')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Preview point awards' })).toBeEnabled())
    await userEvent.click(screen.getByRole('button', { name: 'Preview point awards' }))
    expect(api.generateEventPointAwards).toHaveBeenCalledWith('EVT-2000-W01-wt_a', expect.objectContaining({ dry_run: true, seed: 12345 }))
    const awardsTable = await screen.findByRole('table', { name: 'Event point awards table' })
    expect(within(awardsTable).getByText('champion')).toBeInTheDocument()
    expect(within(awardsTable).getAllByText('1000').length).toBeGreaterThan(0)
    expect(screen.getByText('point_error: point error')).toBeInTheDocument()
    expect(screen.getByText('point_warn: point warning')).toBeInTheDocument()
  })

  it('persists point awards and applies points through API', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    api.getEventEntryList.mockResolvedValue({ ...entryResult, entry_list_exists: true })
    api.getEventDrawPackage.mockResolvedValue({ ...drawResult, draw_package_exists: true })
    api.getEventMatchPackage.mockResolvedValue({ ...simulatedMatchResult, match_package_exists: true })
    api.getEventResultPackage.mockResolvedValue({ ...eventResult, result_package_exists: true })
    api.generateEventPointAwards.mockResolvedValue(persistedPointAwardsResult)
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Manual Artifact Tools \/ Advanced/i)

    await waitFor(() => expect(screen.getByRole('button', { name: 'Persist point awards' })).toBeEnabled())
    await userEvent.click(screen.getByRole('button', { name: 'Persist point awards' }))
    expect(api.generateEventPointAwards).toHaveBeenCalledWith('EVT-2000-W01-wt_a', expect.objectContaining({ dry_run: false }))
    await userEvent.click(await screen.findByRole('button', { name: 'Apply points to active players' }))
    expect(api.applyEventPointAwards).toHaveBeenCalledWith('EVT-2000-W01-wt_a', { seed: 12345, allow_reapply: false })
    const updatesTable = await screen.findByRole('table', { name: 'Applied point updates table' })
    expect(within(updatesTable).getAllByText('1000').length).toBeGreaterThan(0)
  })


  it('renders Ranking Race Tables section and loads table params', async () => {
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')
    await expandAdminSection(/Rankings \/ Snapshots/i)

    expect(await screen.findByRole('heading', { name: 'Ranking / Race Tables' })).toBeInTheDocument()
    expect(screen.getByText('This table is derived from active season player points. Rolling 61-week ranking, best-N selection, weekly snapshots, and movement are not implemented yet.')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getAllByLabelText('Table type')[0], 'race')
    await userEvent.clear(screen.getByLabelText('Top N'))
    await userEvent.type(screen.getByLabelText('Top N'), '50')
    await userEvent.type(screen.getAllByLabelText('Country filter')[0], 'aaa')
    await userEvent.type(screen.getAllByLabelText('Search')[0], 'Adam')
    await userEvent.clear(screen.getByLabelText('Min points'))
    await userEvent.type(screen.getByLabelText('Min points'), '10')
    await userEvent.click(screen.getByLabelText(/Include zero points/i))
    await userEvent.click(screen.getByRole('button', { name: 'Load table' }))

    expect(api.getAdminRankingTable).toHaveBeenLastCalledWith('2000/2001', expect.objectContaining({ table_type: 'race', limit: 50, country_code: 'AAA', search: 'Adam', include_zero_points: false, min_points: 10 }))
    const table = await screen.findByRole('table', { name: 'Ranking race table' })
    expect(within(table).getByText('Adam Ahmed AA01')).toBeInTheDocument()
    expect(screen.getAllByText('Best-N ranking selection not implemented.').length).toBeGreaterThan(0)
  })
})
