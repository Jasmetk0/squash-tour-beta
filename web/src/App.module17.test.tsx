import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

const api = vi.hoisted(() => ({
  getHealth: vi.fn(),
  createRun: vi.fn(),
  getRun: vi.fn(),
  getRunStatusSummary: vi.fn(),
  listRuns: vi.fn(),
  listCountries: vi.fn(),
  getCountriesMetadata: vi.fn(),
  getTournamentTemplatesMetadata: vi.fn(),
  listEvents: vi.fn(),
  getRunActivity: vi.fn(),
  getEvent: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn(),
  getFinalsSummary: vi.fn(),
  getFinalsQualification: vi.fn(),
  getFinalsResult: vi.fn(),
  simulateWorldTourFinals: vi.fn(),
  getLatestRollover: vi.fn(),
  getRolloverBySeason: vi.fn(),
  getPlayerTransitions: vi.fn(),
  getNextSeasonPlayers: vi.fn(),
  rolloverNextSeason: vi.fn(),
  getRunSource: vi.fn(),
  getRunLineage: vi.fn(),
  getRunTalentPlan: vi.fn(),
  listGeneratedPlayersProvenance: vi.fn(),
  bootstrapNextSeason: vi.fn(),
  getViewerRankingTable: vi.fn(),
  getAdminRankingTable: vi.fn(),
  getTalentClassSummary: vi.fn(),
  getSeasonRegistry: vi.fn(),
  getSeasonTemplates: vi.fn(),
  getCategories: vi.fn(),
  getTournaments: vi.fn(),
  getTourSeasonsValidation: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('./api/client', () => api)

function renderAppAt(route: string): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Module 17 pages through routes', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.listRuns.mockResolvedValue({ runs: [] })
    api.listCountries.mockResolvedValue({
      countries: [
        {
          code: 'EGY',
          name: 'Egypt',
          region: 'MENA',
          population: 100000000,
          wealth_support: 5,
          squash_popularity: 5,
          squash_tradition: 5,
          system_quality: 5,
          competition_density: 5,
          federation_quality: 5,
          court_count: 5000,
          travel_region: 'MENA',
          notes: null,
          style_dna: { attacking: 0.8 },
          flag_asset: null
        }
      ]
    })
    api.getCountriesMetadata.mockResolvedValue({ dataset_status: 'temporary_seed_demo', country_count: 0, source_path: 'config/world/countries.json' })
    api.getTournamentTemplatesMetadata.mockResolvedValue({ template_count: 0, source_path: 'config/tournament_templates/mvp_templates.json', referenced_by_calendar: false, referenced_template_ids: [] })
    api.getViewerRankingTable.mockResolvedValue({ rows: [], summary: { season: '2000/2001', table_type: 'ranking', player_count: 0, total_source_players: 0, ranked_player_count: 0, zero_point_players: 0, countries_represented: 0, leader_player_id: null, leader_points: null, generated_from_active_players_fingerprint: 'active-fp', rolling_ranking_implemented: false, best_n_implemented: false, movement_implemented: false }, metadata: { season: '2000/2001', table_type: 'ranking', source: 'season_active_players', active_players_fingerprint: 'active-fp', generated_fingerprint: 'generated-fp', ranking_basis: 'current active season player ranking_points', filters: { country_code: null, search: null, include_zero_points: true, min_points: null }, limit: 100, warnings: [] }, validation_warnings: ['Rolling 61-week ranking not implemented.'], validation_errors: [] })
    api.getTalentClassSummary.mockResolvedValue({ year_start: 2030, years: 10, seed: 123, dataset_status: 'temporary_seed_demo', country_count: 0, source_path: 'config/world/countries.json', total_talents_across_span: 0, average_total_talents_per_year: 0, global_band_totals: {}, global_elite_talents: 0, global_tour_talents: 0, global_pro_depth: 0, countries: [] })
    api.getSeasonRegistry.mockResolvedValue({
      start_season: '2000/01',
      end_season: '2039/40',
      season_count: 40,
      week_count: 61,
      season_week_1_year_week: 37,
      seasons: Array.from({ length: 40 }, (_, index) => ({ season_start_year: 2000 + index, label: `${2000 + index}/${String((2001 + index) % 100).padStart(2, '0')}`, season_index: index, week_count: 61, season_week_start: 1, season_week_end: 61, year_week_start: 37, year_week_end: 36, status: 'registry_only' }))
    })
    api.getCategories.mockResolvedValue({
      categories: [{ category_id: 'gold', name: 'GOLD', status: 'read_only_foundation', source: 'derived_preview:tournament_templates', template_count: 1, valid_from_season: null, valid_to_season: null, tour_level: 'WORLD_TOUR', prestige_rank: null, mandatory: null, main_draw_size: null, qualification_draw_size: 16, direct_entries: 18, qualifiers: 4, wildcards: 2, lucky_losers: 2, seeds_count: 8, points_by_round: null, prize_money_total: null, match_format: null, qualifying_weeks_count: 1, main_draw_weeks_count: null, schedule_footprint_weeks: 1, source_template_ids: ['wt_gold_24'], notes: ['Mixed draw sizes across source templates.'] }],
      source_path: 'config/tournament_templates/mvp_templates.json',
      status: 'read_only_foundation'
    })
    api.getTournaments.mockResolvedValue({
      tournaments: [{ tournament_id: 'world-tour-gold', name: 'World Tour Gold', status: 'read_only_foundation', source: 'derived_preview:tournament_templates', source_template_ids: ['wt_gold_24'], template_count: 1, categories: ['GOLD'], tour_levels: ['WORLD_TOUR'], host_countries: ['ENG'], regions: ['EUROPE'], default_category: null, default_host_country: 'ENG', default_region: 'EUROPE', default_duration_weeks: 1, has_qualification: true, notes: [] }],
      source_path: 'config/tournament_templates/mvp_templates.json',
      status: 'read_only_foundation'
    })
    api.getTourSeasonsValidation.mockResolvedValue({
      status: 'read_only_foundation',
      summary: {
        total_checks: 8,
        warning_count: 2,
        info_count: 3,
        ok_count: 3,
        registry_loaded: true,
        category_count: 1,
        tournament_count: 1,
        season_template_count: 1,
        season_template_slot_count: 1
      },
      sections: [
        { section_id: 'registry', title: 'Registry', issues: [] },
        { section_id: 'category', title: 'Category', issues: [{ issue_id: 'category-gold-notes', severity: 'warning', area: 'category', item_id: 'gold', item_name: 'GOLD', message: 'Notes present in backend validation.', link_hint: '/admin/tour-seasons/categories/gold' }] },
        { section_id: 'tournament', title: 'Tournament', issues: [] },
        { section_id: 'season_template', title: 'Season Template', issues: [] }
      ],
      planned_future: ['Backend validation engine.']
    })
    api.getSeasonTemplates.mockResolvedValue({
      templates: [{ template_id: 'default_msa_template_preview', name: 'Default MSA Template Preview', description: 'Read-only derived preview built from current tournament templates config.', season_count_supported: 40, week_count: 61, slot_count: 1, source: 'derived_preview:tournament_templates', status: 'read_only_foundation', slots: [{ slot_id: 'slot-01-wt_gold_24', season_week_start: 1, season_week_end: 1, duration_weeks: 1, tournament_name: 'World Tour Gold', category: 'GOLD', host_country: 'ENG', region: 'EUROPE', has_qualification: true, qualifying_week_start: 1, main_draw_week_start: 1, source_template_id: 'wt_gold_24', notes: null }] }],
      source_path: 'config/tournament_templates/mvp_templates.json',
      status: 'read_only_foundation'
    })
  })

  it('renders the Phase 1 landing page at root', async () => {
    renderAppAt('/')
    expect(await screen.findByText('Choose how you want to use the deterministic FAX squash world.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Browse the generated squash world/i })).toHaveAttribute('href', '/viewer')
    expect(screen.getByRole('link', { name: /Build, validate, and simulate the world/i })).toHaveAttribute('href', '/admin')
  })

  it('renders the Admin Engine dashboard route', async () => {
    renderAppAt('/admin')
    expect(await screen.findByRole('heading', { name: 'Admin Engine Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Simulate' })).toHaveAttribute('href', '/admin/simulate')
    expect(screen.getByRole('link', { name: 'Tour & Seasons' })).toHaveAttribute('href', '/admin/tour-seasons')
  })

  it('renders Simulate launcher overview concepts without fake results table', async () => {
    renderAppAt('/admin/simulate')
    expect(await screen.findByRole('heading', { name: 'Simulate' })).toBeInTheDocument()
    expect(screen.getByText('Simulation launcher for match, round, tournament, week, season, and full timeline workflows.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Runs' })).toHaveAttribute('href', '/admin/runs')
    expect(screen.getByRole('link', { name: /Match/ })).toHaveAttribute('href', '/admin/runs#match')
    expect(screen.getByRole('link', { name: /Round/ })).toHaveAttribute('href', '/admin/runs#round')
    expect(screen.getByRole('link', { name: /Tournament/ })).toHaveAttribute('href', '/admin/runs#tournament')
    expect(screen.getByRole('link', { name: /^Week/ })).toHaveAttribute('href', '/admin/runs#week')
    expect(screen.getByRole('link', { name: /Season Simulate rest of season/ })).toHaveAttribute('href', '/admin/runs#season')
    expect(screen.getByRole('link', { name: /Full Timeline/ })).toHaveAttribute('href', '/admin/runs#timeline')
    expect(screen.getByText(/Next Tournament/)).toBeInTheDocument()
    expect(screen.getByText(/Next Week/)).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })


  it('renders Diagnostics control center overview with run guidance and category sections', async () => {
    localStorage.setItem('beta_engine:last_run_id', 'run-a')
    renderAppAt('/admin/diagnostics')

    expect(await screen.findByRole('heading', { name: 'Diagnostics' })).toBeInTheDocument()
    expect(
      screen.getByText(
        'Control center for world balance, calendar validation, run health, invalidated data, narrative locks, and audit warnings.'
      )
    ).toBeInTheDocument()
    expect(screen.getByText(/Operational diagnostics currently remain run-scoped in Run Diagnostics/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Runs' })).toHaveAttribute('href', '/admin/runs')
    expect(screen.getByRole('link', { name: /Open last run diagnostics/i })).toHaveAttribute('href', '/admin/runs/run-a/diagnostics')

    expect(screen.getByRole('heading', { name: 'World Balance' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Calendar Validation' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Run Health' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Invalidated Data' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Narrative Locks' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Audit / Warnings' })).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByText(/warning count|error count|total issues/i)).not.toBeInTheDocument()
  })
  it('renders Tour & Seasons hub and shell routes while keeping operational routes available', async () => {
    renderAppAt('/admin/tour-seasons')
    expect(await screen.findByRole('heading', { name: 'Tour & Seasons' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Categories/ })).toHaveAttribute('href', '/admin/tour-seasons/categories')
    expect(screen.getByRole('link', { name: /Tournaments/ })).toHaveAttribute('href', '/admin/tour-seasons/tournaments')
    expect(screen.getByRole('link', { name: /Season Templates/ })).toHaveAttribute('href', '/admin/tour-seasons/season-templates')
    expect(screen.getByRole('link', { name: /Season Registry/ })).toHaveAttribute('href', '/admin/tour-seasons/season-registry')
    expect(screen.getByRole('link', { name: /Seasons Concrete 61-week season calendars/ })).toHaveAttribute('href', '/admin/seasons')
    expect(screen.getByRole('link', { name: /Calendar Compare \/ Apply/ })).toHaveAttribute('href', '/admin/tour-seasons/compare')
    expect(screen.getByRole('link', { name: /Calendar Validation/ })).toHaveAttribute('href', '/admin/tour-seasons/validation')

    renderAppAt('/admin/tour-seasons/categories')
    expect(await screen.findByRole('heading', { name: 'Categories' })).toBeInTheDocument()
    expect(screen.getAllByText(/Read-only foundation\./).length).toBeGreaterThan(0)
    expect(await screen.findByRole('link', { name: /GOLD \(gold\)/ })).toHaveAttribute('href', '/admin/tour-seasons/categories/gold')
    expect(screen.getAllByRole('link', { name: 'Open Tournament Templates' })[0]).toHaveAttribute('href', '/admin/tournament-templates')
    expect(screen.getAllByRole('link', { name: 'Open Season Templates' })[0]).toHaveAttribute('href', '/admin/tour-seasons/season-templates')

    renderAppAt('/admin/tour-seasons/tournaments')
    expect(await screen.findByRole('heading', { name: 'Tournaments' })).toBeInTheDocument()
    expect(screen.getByText(/Read-only tournament master records derived from current tournament template config\./)).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: /World Tour Gold \(world-tour-gold\)/ })).toHaveAttribute('href', '/admin/tour-seasons/tournaments/world-tour-gold')
    expect(screen.getAllByRole('link', { name: 'Open Tournament Templates' })[0]).toHaveAttribute('href', '/admin/tournament-templates')
    expect(screen.getByRole('link', { name: 'Open Categories' })).toHaveAttribute('href', '/admin/tour-seasons/categories')
    expect(screen.getAllByRole('link', { name: 'Open Season Templates' })[0]).toHaveAttribute('href', '/admin/tour-seasons/season-templates')


    renderAppAt('/admin/tour-seasons/season-templates')
    expect(await screen.findByRole('heading', { name: 'Season Templates' })).toBeInTheDocument()
    expect(screen.getAllByText(/Read-only foundation\./).length).toBeGreaterThan(0)
    expect((await screen.findAllByText(/Source path: config\/tournament_templates\/mvp_templates\.json/)).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /Default MSA Template Preview \(default_msa_template_preview\)/ })).toHaveAttribute('href', '/admin/tour-seasons/season-templates/default_msa_template_preview')
    expect(screen.getByRole('link', { name: 'Open Season Registry' })).toHaveAttribute('href', '/admin/tour-seasons/season-registry')
    expect(screen.getByRole('link', { name: 'Open Seasons' })).toHaveAttribute('href', '/admin/seasons')


    renderAppAt('/admin/tour-seasons/season-registry')
    expect(await screen.findByRole('heading', { level: 2, name: 'Season Registry' })).toBeInTheDocument()
    expect(screen.getByText(/fixed 2000\/01–2039\/40 MSA season model\./)).toBeInTheDocument()
    expect(await screen.findByRole('cell', { name: '2000/01' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '2039/40' })).toBeInTheDocument()
    expect(screen.getByText(/SW1 → YW37/)).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Season' })).toBeInTheDocument()
    expect(screen.getByRole('cell', { name: '2000/01' })).toBeInTheDocument()

    renderAppAt('/admin/tour-seasons/compare')
    expect(await screen.findByRole('heading', { name: 'Calendar Compare / Apply' })).toBeInTheDocument()
    expect(screen.getByText(/Read-only comparison foundation for templates, registry seasons, and future concrete season calendars\./)).toBeInTheDocument()
    expect(await screen.findByText('Registry range')).toBeInTheDocument()
    expect(await screen.findByText('2000/01–2039/40')).toBeInTheDocument()
    expect(screen.getByText('Registry season count')).toBeInTheDocument()
    expect(screen.getByText('Registry week count')).toBeInTheDocument()
    expect(screen.getByText('Season templates count')).toBeInTheDocument()
    expect(screen.getByText('Default MSA Template Preview')).toBeInTheDocument()
    expect(screen.getByText('Planned statuses: Same, Modified, Missing from current, Only in current, and Conflict.')).toBeInTheDocument()
    expect(screen.getByText('Planned actions: Apply to this season, Replace current, Keep current, Ignore, and Open editor.')).toBeInTheDocument()
    expect(screen.getByText('These actions are planned and not enabled.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /apply|replace|keep current|ignore|open editor|save|update|delete|create/i })).not.toBeInTheDocument()

    renderAppAt('/admin/tour-seasons/validation')
    expect(await screen.findByRole('heading', { name: 'Calendar Validation' })).toBeInTheDocument()
    expect(screen.getByText('Read-only validation overview for Tour & Seasons foundation data.')).toBeInTheDocument()
    expect(await screen.findByText('Categories: 1')).toBeInTheDocument()
    expect((await screen.findAllByText('Tournaments: 1')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Season Templates: 1')).toBeInTheDocument()
    expect(await screen.findByText(/Season Template Slots \(total\): 1/)).toBeInTheDocument()
    expect(await screen.findByText('Total checks: 7')).toBeInTheDocument()
    expect(await screen.findByText('Warnings: 1')).toBeInTheDocument()
    expect((await screen.findAllByText('Info: 3')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('OK: 3')).length).toBeGreaterThan(0)
    expect(await screen.findByRole('heading', { name: 'Backend validation foundation' })).toBeInTheDocument()
    expect(screen.getAllByText('Status: read_only_foundation').length).toBeGreaterThan(0)
    expect(screen.getByText('Total checks: 8')).toBeInTheDocument()
    expect(screen.getByText('Warnings: 2')).toBeInTheDocument()
    expect(screen.getAllByText('Info: 3').length).toBeGreaterThan(0)
    expect(screen.getAllByText('OK: 3').length).toBeGreaterThan(0)
    expect(screen.getByText('Sections returned: 4')).toBeInTheDocument()
    expect(screen.getByText('Frontend-derived total checks: 7')).toBeInTheDocument()
    expect(screen.getByText('Backend total checks: 8')).toBeInTheDocument()
    expect(screen.getByText('Comparison only; both systems are read-only.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Backend validation issue preview' })).toBeInTheDocument()
    const backendIssuePreviewSummary = screen.getByText('Show backend issue preview')
    expect(backendIssuePreviewSummary).toBeInTheDocument()
    expect(screen.getByText('Secondary preview only. Frontend-derived checks remain primary until backend validation becomes authoritative.')).not.toBeVisible()
    expect(screen.getByRole('link', { name: 'Notes present in backend validation.' })).not.toBeVisible()
    fireEvent.click(backendIssuePreviewSummary)
    expect(screen.getByText('Secondary preview only. Frontend-derived checks remain primary until backend validation becomes authoritative.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Notes present in backend validation.' })).toHaveAttribute('href', '/admin/tour-seasons/categories/gold')
    expect(screen.getByText(/Frontend-derived checks remain visible below until backend validation becomes the authoritative source\./)).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'All' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Warnings' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Info' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'OK' })).toBeInTheDocument()
    expect(await screen.findByText(/\[Warning\] Category/)).toBeInTheDocument()
    expect(await screen.findByText(/\[Info\] Tournament/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Warnings' }))
    expect(screen.getByText(/\[Warning\] Category/)).toBeInTheDocument()
    expect(screen.queryByText(/\[Info\] Tournament/)).not.toBeInTheDocument()
    expect(screen.getAllByText('No checks match the current filter.').length).toBeGreaterThan(0)

    fireEvent.click(screen.getByRole('button', { name: 'Info' }))
    expect(screen.getByText(/\[Info\] Tournament/)).toBeInTheDocument()
    expect(screen.queryByText(/\[Warning\] Category/)).not.toBeInTheDocument()

    expect(screen.getAllByRole('link', { name: /GOLD \(gold\)/ })[0]).toHaveAttribute('href', '/admin/tour-seasons/categories/gold')
    expect(screen.getAllByRole('link', { name: /World Tour Gold \(world-tour-gold\)/ })[0]).toHaveAttribute('href', '/admin/tour-seasons/tournaments/world-tour-gold')
    expect(screen.queryByRole('button', { name: /apply|save|update|delete|create/i })).not.toBeInTheDocument()
  })





  it('renders category detail route and not-found route', async () => {
    renderAppAt('/admin/tour-seasons/categories/gold')
    expect(await screen.findByRole('heading', { name: 'Category' })).toBeInTheDocument()
    expect(await screen.findByText(/Name: GOLD/)).toBeInTheDocument()
    expect(screen.getByText(/category_id: gold/)).toBeInTheDocument()
    expect(screen.getAllByText(/read_only_foundation/).length).toBeGreaterThan(0)
    expect(screen.getByText(/main_draw_size:/)).toBeInTheDocument()
    expect(screen.getByText('Category editor — planned.')).toBeInTheDocument()
    expect(screen.getByText('Category versioning by season range — planned.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Categories' })).toHaveAttribute('href', '/admin/tour-seasons/categories')
    expect(screen.getByRole('link', { name: 'Open Tournament Templates' })).toHaveAttribute('href', '/admin/tournament-templates')
    expect(screen.getByRole('link', { name: 'Open Tournaments' })).toHaveAttribute('href', '/admin/tour-seasons/tournaments')
    expect(screen.getByRole('link', { name: 'Open Season Templates' })).toHaveAttribute('href', '/admin/tour-seasons/season-templates')

    renderAppAt('/admin/tour-seasons/categories/unknown-id')
    expect(await screen.findByText('Category not found.')).toBeInTheDocument()
  })

  it('renders tournament master detail route and not-found route', async () => {
    renderAppAt('/admin/tour-seasons/tournaments/world-tour-gold')
    expect(await screen.findByRole('heading', { name: 'Tournament Master' })).toBeInTheDocument()
    expect(await screen.findByText(/tournament_id: world-tour-gold/)).toBeInTheDocument()
    expect(screen.getAllByText(/read_only_foundation/).length).toBeGreaterThan(0)
    expect(screen.getByText('Tournament master editor — planned.')).toBeInTheDocument()
    expect(screen.getByText('Tournament editions — planned.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Tournaments' })).toHaveAttribute('href', '/admin/tour-seasons/tournaments')
    expect(screen.getByRole('link', { name: 'Open Tournament Templates' })).toHaveAttribute('href', '/admin/tournament-templates')
    expect(screen.getByRole('link', { name: 'Open Categories' })).toHaveAttribute('href', '/admin/tour-seasons/categories')
    expect(screen.getByRole('link', { name: 'Open Season Templates' })).toHaveAttribute('href', '/admin/tour-seasons/season-templates')

    renderAppAt('/admin/tour-seasons/tournaments/unknown-id')
    expect(await screen.findByText('Tournament master not found.')).toBeInTheDocument()
  })


  it('renders season template detail route and not-found route', async () => {
    renderAppAt('/admin/tour-seasons/season-templates/default_msa_template_preview')
    expect(await screen.findByRole('heading', { name: 'Season Template' })).toBeInTheDocument()
    expect((await screen.findAllByText(/Default MSA Template Preview/)).length).toBeGreaterThan(0)
    expect(await screen.findByText('Template ID: default_msa_template_preview')).toBeInTheDocument()
    expect(screen.getAllByText(/read_only_foundation/).length).toBeGreaterThan(0)
    expect(screen.getByText('Season template editor — planned.')).toBeInTheDocument()
    expect(screen.getByText('Copy/apply to concrete season — planned.')).toBeInTheDocument()
    expect(screen.getByText('Compare/apply workflows — planned.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Season Templates' })).toHaveAttribute('href', '/admin/tour-seasons/season-templates')
    expect(screen.getByRole('link', { name: 'Open Tournaments' })).toHaveAttribute('href', '/admin/tour-seasons/tournaments')
    expect(screen.getByRole('link', { name: 'Open Categories' })).toHaveAttribute('href', '/admin/tour-seasons/categories')
    expect(screen.getByRole('link', { name: 'Open Seasons' })).toHaveAttribute('href', '/admin/seasons')

    renderAppAt('/admin/tour-seasons/season-templates/unknown-id')
    expect(await screen.findByText('Season template not found.')).toBeInTheDocument()
  })

  it('renders Players hub route with Talent Intake and Player Database links', async () => {
    renderAppAt('/admin/players')
    expect(await screen.findByRole('heading', { name: 'Players' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Player Database/i })).toHaveAttribute('href', '/admin/players/database')
    expect(screen.getByRole('link', { name: /Talent Intake/i })).toHaveAttribute('href', '/admin/players/intake')
  })

  it('renders Talent Intake shell route with workflow steps and no fake table data', async () => {
    renderAppAt('/admin/players/intake')
    expect(await screen.findByRole('heading', { name: 'Talent Intake' })).toBeInTheDocument()
    expect(screen.getByText('Select Season')).toBeInTheDocument()
    expect(screen.getByText('Generate Preview')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('renders world hub cards for Countries and Talent Preview', async () => {
    renderAppAt('/admin/world')
    expect(await screen.findByRole('heading', { name: 'World' })).toBeInTheDocument()
    expect(screen.getByText('Manage country inputs and expected talent output used by the FAX squash simulation engine.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Countries Edit country inputs/i })).toHaveAttribute('href', '/admin/world/countries')
    expect(screen.getByRole('link', { name: /Talent Preview Preview expected Elite Talents/i })).toHaveAttribute('href', '/admin/world/talent-preview')
    expect(screen.queryByRole('link', { name: 'Country Momentum' })).not.toBeInTheDocument()
  })

  it('renders country detail route for existing country code', async () => {
    renderAppAt('/admin/world/countries/EGY')
    expect(await screen.findByRole('heading', { name: 'Egypt (EGY)' })).toBeInTheDocument()
    expect(screen.getByText(/Country profile and authored model inputs/i)).toBeInTheDocument()
  })

  it('renders the Viewer MSA home route with no active run empty state', async () => {
    localStorage.removeItem('beta_engine:viewer_active_run_id')
    api.listRuns.mockResolvedValueOnce({ runs: [] })
    renderAppAt('/viewer')
    expect(await screen.findByRole('heading', { name: 'MSA Website Home' })).toBeInTheDocument()
    expect(screen.getByText('Select a Viewer run first to enable run-scoped MSA website links.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Rankings' })).toHaveAttribute('href', '/viewer/rankings')
    expect(screen.queryByRole('link', { name: 'Players' })).toHaveAttribute('href', '/viewer/players')
    expect(screen.queryByRole('link', { name: 'Countries' })).toHaveAttribute('href', '/viewer/countries')
    expect(screen.queryByRole('link', { name: 'History' })).toHaveAttribute('href', '/viewer/history')
    expect(screen.queryByRole('link', { name: 'Finals' })).not.toBeInTheDocument()
  })

  it('renders the Viewer MSA home route with active run links', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'viewer-run-1')
    api.listRuns.mockResolvedValueOnce({ runs: [] })
    renderAppAt('/viewer')
    expect(await screen.findByRole('heading', { name: 'MSA Website Home' })).toBeInTheDocument()
    expect(screen.getAllByText(/viewer-run-1/)[0]).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Rankings' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-1/rankings')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Tournaments' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-1/tournaments')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Players' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-1/players')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Countries' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-1/countries')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'History' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-1/history')).toBe(true)
  })

  it('renders top-level Viewer rankings with active run link', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'viewer-run-2')
    renderAppAt('/viewer/rankings')
    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Rankings' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-2/rankings')).toBe(true)
  })

  beforeEach(() => {
    api.getEvent.mockResolvedValue({ event_sequence: 2, event_id: 'E2', season: 2027, week: 9, template_id: null, tournament_result: {} })
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2027, seed: 5, next_event_index: 1, total_events: 10, completed_event_ids: [] },
      season_state: { season: 2027, next_event_index: 1, completed_event_ids: [], ordered_events: [] }
    })
    api.getRunStatusSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      seed: 5,
      progress: { next_event_index: 1, total_events: 10, completed_event_count: 0 },
      finals: { qualification_available: false, result_available: false },
      rollover: null,
      source: null,
      lineage: { child_run_count: 0 },
      history_counts: { events: 0, ranking_snapshots: 1, race_snapshots: 1 }
    })
    api.listEvents.mockResolvedValue({ events: [] })
    api.getFinalsSummary.mockResolvedValue({ run_id: 'run-a', season: 2027, qualification: {}, result: null })
    api.getFinalsQualification.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      source_as_of_season: 2027,
      source_as_of_week: 42,
      qualification: { qualified_player_ids: ['P1'] }
    })
    api.getFinalsResult.mockRejectedValue(new Error('no result yet'))
    api.getLatestRollover.mockRejectedValue(new Error('no rollover'))
    api.getRolloverBySeason.mockResolvedValue({
      rollover: { run_id: 'run-a', from_season: 2027, to_season: 2028, transitioned_players: 64, metadata: {} }
    })
    api.getPlayerTransitions.mockResolvedValue({ run_id: 'run-a', to_season: 2028, transitions: [] })
    api.getNextSeasonPlayers.mockResolvedValue({ run_id: 'run-a', to_season: 2028, players: [] })
    api.getRunSource.mockResolvedValue({
      source: {
        source_type: 'new_run',
        parent_run_id: null,
        source_rollover_run_id: null,
        source_rollover_from_season: null,
        source_rollover_to_season: null
      }
    })
    api.getRunLineage.mockResolvedValue({
      lineage: {
        run_id: 'run-a',
        source: {
          source_type: 'new_run',
          parent_run_id: null,
          source_rollover_run_id: null,
          source_rollover_from_season: null,
          source_rollover_to_season: null
        },
        children: []
      }
    })
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [{ snapshot_sequence: 4, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: { name: 'ranking-4' } }]
    })
    api.listRaceSnapshots.mockResolvedValue({
      snapshots: [{ snapshot_sequence: 7, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: { name: 'race-7' } }]
    })
    api.getRunTalentPlan.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      seed: 5,
      total_talents: 1,
      dataset_status: 'active',
      config_version: 'cfg',
      config_fingerprint: 'fp',
      countries: [
        {
          country_code: 'EGY',
          planned_count: 1,
          quality_weights: { solid_prospect: 1 },
          actual_band_counts: { solid_prospect: 1 },
          bias_profile: {}
        }
      ]
    })
    api.listGeneratedPlayersProvenance.mockResolvedValue({
      run_id: 'run-a',
      players: [
        {
          run_id: 'run-a',
          season: 2027,
          player_id: 'EGY-00001',
          country_code: 'EGY',
          talent_sequence: 1,
          talent_seed_value: 1,
          quality_band: 'solid_prospect',
          is_top_band: false
        }
      ]
    })
  })

  it('renders Finals route', async () => {
    renderAppAt('/runs/run-a/finals')
    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
  })

  it('renders Finals qualification detail route', async () => {
    renderAppAt('/runs/run-a/finals/qualification')
    expect(await screen.findByRole('heading', { name: 'Finals qualification detail' })).toBeInTheDocument()
  })

  it('renders Finals result detail route', async () => {
    api.getFinalsResult.mockResolvedValueOnce({
      run_id: 'run-a',
      season: 2027,
      event_id: 'WORLD_TOUR_FINALS',
      source_as_of_season: 2027,
      source_as_of_week: 42,
      result: { champion_player_id: 'P1' }
    })
    renderAppAt('/runs/run-a/finals/result')
    expect(await screen.findByRole('heading', { name: 'Finals result detail' })).toBeInTheDocument()
  })

  it('renders Rollover route', async () => {
    renderAppAt('/runs/run-a/rollover')
    expect(await screen.findByRole('heading', { name: 'Season Rollover' })).toBeInTheDocument()
  })


  it('renders rollover season detail route', async () => {
    renderAppAt('/runs/run-a/rollover/2028')
    expect(await screen.findByRole('heading', { name: 'Rollover season detail' })).toBeInTheDocument()
  })

  it('renders diagnostics route', async () => {
    renderAppAt('/runs/run-a/diagnostics')
    expect(await screen.findByRole('heading', { name: 'Run diagnostics' })).toBeInTheDocument()
  })

  it('renders world generation route', async () => {
    renderAppAt('/runs/run-a/world-generation')
    expect(await screen.findByRole('heading', { name: 'World generation diagnostics' })).toBeInTheDocument()
  })

  it('renders runs browser route', async () => {
    api.listRuns.mockResolvedValueOnce({ runs: [] })
    renderAppAt('/runs')
    expect(await screen.findByRole('heading', { name: 'Runs browser' })).toBeInTheDocument()
  })

  it('renders activity route', async () => {
    api.getRunActivity.mockResolvedValue({ run_id: 'run-a', items: [] })
    renderAppAt('/runs/run-a/activity')
    expect(await screen.findByRole('heading', { name: 'Run activity' })).toBeInTheDocument()
  })

  it('renders season calendar route', async () => {
    renderAppAt('/runs/run-a/calendar')
    expect(await screen.findByRole('heading', { name: 'Season calendar' })).toBeInTheDocument()
  })

  it('renders week detail route', async () => {
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run-a', season: 2027, seed: 5, next_event_index: 0, total_events: 2, completed_event_ids: [] },
      season_state: {
        season: 2027,
        next_event_index: 0,
        completed_event_ids: [],
        ordered_events: [
          { event_id: 'E2', season: 2027, week: 9, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP' },
          { event_id: 'E3', season: 2027, week: 10, tour: 'WORLD', category: 'SILVER', template_id: 'TEMP2' }
        ]
      }
    })
    renderAppAt('/runs/run-a/weeks/9')
    expect(await screen.findByRole('heading', { name: 'Week detail' })).toBeInTheDocument()
  })

  it('renders Bootstrap/Lineage route', async () => {
    renderAppAt('/runs/run-a/bootstrap-lineage')
    expect(await screen.findByRole('heading', { name: 'Bootstrap / Lineage' })).toBeInTheDocument()
  })


  it('renders Season Chain route', async () => {
    renderAppAt('/runs/run-a/season-chain')
    expect(await screen.findByRole('heading', { name: 'Season Chain' })).toBeInTheDocument()
  })



  it('renders planned event detail route', async () => {
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run-a', season: 2027, seed: 5, next_event_index: 0, total_events: 1, completed_event_ids: [] },
      season_state: {
        season: 2027,
        next_event_index: 0,
        completed_event_ids: [],
        ordered_events: [{ event_id: 'E2', season: 2027, week: 9, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP' }]
      }
    })
    renderAppAt('/runs/run-a/calendar/E2')
    expect(await screen.findByRole('heading', { name: 'Planned event detail' })).toBeInTheDocument()
  })

  it('renders Event detail route', async () => {
    renderAppAt('/runs/run-a/events/E2')
    expect(await screen.findByRole('heading', { name: 'Event detail' })).toBeInTheDocument()
  })

  it('renders ranking snapshot detail route', async () => {
    renderAppAt('/runs/run-a/snapshots/ranking/4')
    expect(await screen.findByRole('heading', { name: 'Ranking snapshot detail' })).toBeInTheDocument()
  })

  it('renders race snapshot detail route', async () => {
    renderAppAt('/runs/run-a/snapshots/race/7')
    expect(await screen.findByRole('heading', { name: 'Race snapshot detail' })).toBeInTheDocument()
  })
})
