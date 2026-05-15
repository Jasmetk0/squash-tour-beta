import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminSeasonsPage } from './AdminSeasonsPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getSeasonActivePlayers: vi.fn(),
  bootstrapSeasonFromInitialPool: vi.fn(),
  getSeasonCalendar: vi.fn(),
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
  year_week: 35,
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
    event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', season_week: 1, calendar_year: 2000, year_week: 35, template_id: 'wt_a', generated_from_calendar_fingerprint: 'calendar-fp', generated_from_active_players_fingerprint: 'active-fp', seed: 12345, dry_run: true, persisted: false,
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
    event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', template_id: 'wt_a', season_week: 1, calendar_year: 2000, year_week: 35, seed: 12345, dry_run: true, persisted: false,
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
    event_id: 'EVT-2000-W01-wt_a', season: '2000/2001', template_id: 'wt_a', season_week: 1, calendar_year: 2000, year_week: 35, seed: 12345, dry_run: true, persisted: false, qualification_matches: [], main_draw_matches: [matchRecord],
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
  metadata: { season: '2000/2001', season_start_calendar_year: 2000, season_start_year_week: 35, total_season_weeks: 61, event_count: 1, build_seed: 12345, build_fingerprint: 'calendar-fp', source_template_count: 1, persistence_path: null, dry_run: true, overwrite_existing: false },
  validation_warnings: [{ severity: 'warning', code: 'ranking_race_not_integrated', message: 'ranking/race integration not implemented yet', event_id: null, field: null }],
  validation_errors: [{ severity: 'error', code: 'example_error', message: 'example error', event_id: null, field: null }]
}

describe('AdminSeasonsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSeasonActivePlayers.mockResolvedValue(empty)
    api.bootstrapSeasonFromInitialPool.mockResolvedValue(response)
    api.getSeasonCalendar.mockResolvedValue(emptyCalendar)
    api.buildSeasonCalendar.mockResolvedValue(calendarResponse)
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

  it('renders Event Entries section and previews entries', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')

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

    await userEvent.click(await screen.findByRole('button', { name: 'Persist entries' }))
    expect(api.generateEventEntryList).toHaveBeenCalledWith('EVT-2000-W01-wt_a', expect.objectContaining({ dry_run: false }))
  })


  it('renders Event Draws section and previews draws', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    api.getEventEntryList.mockResolvedValue({ ...entryResult, entry_list_exists: true })
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')

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

    await userEvent.click(await screen.findByRole('button', { name: 'Persist draw' }))
    expect(api.generateEventDrawPackage).toHaveBeenCalledWith('EVT-2000-W01-wt_a', expect.objectContaining({ dry_run: false }))
  })


  it('renders Event Matches section and previews match package', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    api.getEventEntryList.mockResolvedValue({ ...entryResult, entry_list_exists: true })
    api.getEventDrawPackage.mockResolvedValue({ ...drawResult, draw_package_exists: true })
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')

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

    await userEvent.click(await screen.findByRole('button', { name: 'Persist match package' }))
    expect(api.generateEventMatchPackage).toHaveBeenCalledWith('EVT-2000-W01-wt_a', expect.objectContaining({ dry_run: false }))
  })

  it('renders progression status and calls progression command APIs', async () => {
    api.getSeasonCalendar.mockResolvedValue(calendarResponse)
    api.getEventEntryList.mockResolvedValue({ ...entryResult, entry_list_exists: true })
    api.getEventDrawPackage.mockResolvedValue({ ...drawResult, draw_package_exists: true })
    api.getEventMatchPackage.mockResolvedValue({ ...matchResult, match_package_exists: true })
    renderWithRoute(<AdminSeasonsPage />, '/admin/seasons')

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

    await userEvent.click(await screen.findByRole('button', { name: 'Simulate next pending match' }))
    expect(api.simulateNextEventMatch).toHaveBeenCalledWith('EVT-2000-W01-wt_a', { seed: 12345 })
    expect(await screen.findByText('11-7, 11-8, 11-9')).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText('Selected match'), 'm1')
    await userEvent.click(screen.getByRole('button', { name: 'Simulate selected match' }))
    expect(api.simulateEventMatch).toHaveBeenCalledWith('EVT-2000-W01-wt_a', 'm1', { seed: 12345 })
  })

})
