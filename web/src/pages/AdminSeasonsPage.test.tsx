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
  generateEventEntryList: vi.fn()
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

})
