import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunPage } from './RunPage'
import { renderWithRoute as renderRoute } from '../test/testUtils'
import { AdminBranchProvider } from '../admin/AdminBranchContext'
import { AdminTimeProvider } from '../admin/AdminTimeContext'
import { AdminTimeControl } from '../components/AdminTimeControl'
import { LanguageProvider } from '../i18n/LanguageContext'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) { super(message); this.status = status }
  },
  getRunContainer: vi.fn(), listRunBranches: vi.fn(), getBranchState: vi.fn(), listBranchCheckpoints: vi.fn(), getRunHomeActivity: vi.fn(), getRunHomeRankingChanges: vi.fn(), getSavedHomePlayerIdentities: vi.fn(),
  getBranchWorkingDraft: vi.fn(), getRunPackageState: vi.fn(), getAuthoritativeSimulationPosition: vi.fn(),
  getPendingAuthoritativeFullSimulations: vi.fn(), getAuthoritativeFullSimulationHistory: vi.fn(), listSavedRevisionHistory: vi.fn()
}))
vi.mock('../api/client', () => api)
vi.mock('../components/RunPackageSetupPanel', () => ({ RunPackageSetupPanel: () => <p>World and Calendar copies</p> }))
vi.mock('../components/RunInitialRankingSetupPanel', () => ({ RunInitialRankingSetupPanel: () => <p>Ranking setup</p> }))
vi.mock('../components/RunInitialRankingPublicationPanel', () => ({ RunInitialRankingPublicationPanel: () => <p>Ranking publication</p> }))
vi.mock('../components/RunFirstTournamentPanel', () => ({ RunFirstTournamentPanel: () => <p>First tournament setup</p> }))

const runId = 'run-home-test'
const branchId = 'branch-home-test'
function mount() {
  return renderRoute(
    <LanguageProvider><AdminBranchProvider runId={runId}><AdminTimeProvider>
      <AdminTimeControl/><RunPage/>
    </AdminTimeProvider></AdminBranchProvider></LanguageProvider>,
    '/admin/runs/' + runId
  )
}
function refPosition(overrides: Record<string, unknown> = {}) {
  return {
    run_id: runId, branch_id: branchId, current_week: { season_index: 2, week: 4 },
    current_slot_kind: 'match', current_slot_id: 'week2-match', eligible_match_ids: ['m1', 'm2'],
    blocked_match_ids: [], unresolved_group_ids: [], transition_blockers: [],
    week_ready_for_transition: false,
    ...overrides
  }
}
describe('Run Home V1 canonical projections', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    api.getRunContainer.mockResolvedValue({
      run_id: runId, display_name: 'Demo Run', storage_kind: 'custom_local',
      read_only: false, status: 'working', official_branch_id: branchId
    })
    api.listRunBranches.mockResolvedValue({ run_branches: [{
      run_id: runId, branch_id: branchId, display_name: 'Timeline 1', status: 'active',
      saved_head_revision_id: 'saved-1', head_checkpoint_id: 'cp-current',
      read_only: false, is_official: true
    }] })
    api.getBranchState.mockResolvedValue({
      run_id: runId, branch_id: branchId, current_season: 2, current_week: 4,
      current_event_id: null, current_event_sequence: null, head_checkpoint_id: 'cp-current'
    })
    api.listBranchCheckpoints.mockResolvedValue({ branch_checkpoints: [{
      checkpoint_id: 'cp-past', run_id: runId, branch_id: branchId, sequence: 1,
      kind: 'completed_week', command_kind: 'week_transition', season: 1, week: 60
    }] })
    api.getBranchWorkingDraft.mockResolvedValue({
      run_id: runId, branch_id: branchId, draft_version: 1, status: 'clean', change_count: 0
    })
    api.getRunPackageState.mockResolvedValue({ state: { run_id: runId, branch_id: branchId }, fingerprint: 'p' })
    api.getAuthoritativeSimulationPosition.mockResolvedValue(refPosition())
    api.getPendingAuthoritativeFullSimulations.mockResolvedValue({ run_id: runId, branch_id: branchId, operations: [] })
    api.getAuthoritativeFullSimulationHistory.mockResolvedValue({ run_id: runId, branch_id: branchId, items: [] })
    api.getRunHomeRankingChanges.mockResolvedValue({
      schema_version: 'run_home_ranking_changes.v1', run_id: runId, branch_id: branchId,
      saved_revision_id: 'saved-1', source: 'selected_branch_saved_revision',
      status: 'unpublished', previous_week_ordinal: null, current_week_ordinal: null,
      current_row_count: null, total_change_count: 0, moved_count: 0,
      entered_count: 0, exited_count: 0, points_only_count: 0, changes: []
    })
    api.getSavedHomePlayerIdentities.mockImplementation(async (_runId: string, _branchId: string, ids: string[]) => ({
      schema_version: 'run_home_player_identities.v1', run_id: runId, branch_id: branchId,
      saved_revision_id: 'saved-1', source: 'selected_branch_saved_revision',
      status: 'unavailable', requested_ids: ids, players: [], unresolved_ids: ids,
    }))
    api.getRunHomeActivity.mockResolvedValue({
      schema_version: 'run_home_activity.v1', run_id: runId, branch_id: branchId,
      saved_revision_id: 'saved-1', source: 'selected_branch_saved_revision',
      calendar_status: 'empty', result_status: 'empty', ranking_changes_status: 'unsupported',
      total_calendar_events: 0, published_result_count: 0, upcoming: [], recent_results: []
    })
    api.listSavedRevisionHistory.mockResolvedValue({ run_id: runId, branch_id: branchId, saved_revisions: [{
      revision_id: 'saved-1', kind: 'initial', sequence: 1, created_at: '2026-10-10'
    }] })
  })

  it('renders 50 seasons and 61 weeks from canonical BranchState, not legacy Run position', async () => {
    mount()
    expect(await screen.findByText('Demo Run')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('2002/03 · 50 sezón')).toBeInTheDocument())
    expect(screen.getByText('W4 · 61 týdnů')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: '50 sezón' }).children).toHaveLength(50)
    expect(screen.getByRole('img', { name: '61 týdnů' }).children).toHaveLength(61)
    expect(screen.getByText('Hratelné zápasy: 2')).toBeInTheDocument()
    expect(screen.getByText('World and Calendar copies')).toBeInTheDocument()
    expect(screen.getByRole('link',{name:'Generovat hráče →'})).toHaveAttribute('href','/admin/runs/'+runId+'/players/generate')
    expect(api.getRunContainer).toHaveBeenCalledWith(runId)
  })

  it('allows a legitimate empty Run without inventing zero matches or a season position', async () => {
    api.getBranchState.mockResolvedValue({
      run_id: runId, branch_id: branchId, current_season: null, current_week: null,
      head_checkpoint_id: null
    })
    api.getRunPackageState.mockResolvedValue({ state: null, fingerprint: null })
    api.getAuthoritativeSimulationPosition.mockRejectedValue(new api.ApiError('No position yet', 404))
    mount()
    expect(await screen.findByText('Prázdný Run je platný.', { exact: false })).toBeInTheDocument()
    expect(screen.getAllByText(/^Zatím neurčeno ·/).length).toBe(2)
    expect(screen.queryByText('Hratelné zápasy: 0')).not.toBeInTheDocument()
    expect(screen.getByRole('img', { name: '50 sezón' }).children).toHaveLength(50)
  })

  it('exposes dirty Viewer-Branch draft and real blockers without claiming all clean', async () => {
    api.getBranchWorkingDraft.mockResolvedValue({ run_id: runId, branch_id: branchId, status: 'dirty', change_count: 2 })
    api.getAuthoritativeSimulationPosition.mockResolvedValue(refPosition({
      transition_blockers: ['Rankings not published'],
      blocked_match_ids: ['match-blocked']
    }))
    mount()
    expect(await screen.findByText('Neuložené změny (2)')).toBeInTheDocument()
    expect(await screen.findByText(/Rankings not published/)).toBeInTheDocument()
    expect(screen.getByText(/Blokované zápasy: 1/)).toBeInTheDocument()
    expect(screen.queryByText(/Načtená data nehlásí žádný aktuální blokátor/)).not.toBeInTheDocument()
  })

  it('keeps request failures distinct from legitimate empty data', async () => {
    api.getAuthoritativeSimulationPosition.mockRejectedValue(new Error('Position projection unavailable'))
    api.getBranchWorkingDraft.mockRejectedValue(new Error('Working Draft unavailable'))
    mount()
    const alerts = await screen.findAllByRole('alert')
    expect(alerts.some(alert => /Working Draft unavailable|Position projection unavailable/.test(alert.textContent ?? ''))).toBe(true)
    expect(screen.queryByText(/Načtená data nehlásí žádný aktuální blokátor/)).not.toBeInTheDocument()
  })

  it('shows checkpoint metadata only in historical Time without current event panels', async () => {
    mount()
    await screen.findByRole('option', { name: /#1/ })
    fireEvent.change(screen.getByRole('combobox', { name: 'Admin Time context' }), { target: { value: 'cp-past' } })
    expect(await screen.findByText(/Historické výsledky a stavy/)).toBeInTheDocument()
    expect(screen.getByText('2001/02 · 50 sezón')).toBeInTheDocument()
    expect(screen.getByText('W60 · 61 týdnů')).toBeInTheDocument()
    expect(screen.queryByText('Hratelné zápasy: 2')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Vrátit se do současnosti' }))
    await waitFor(() => expect(screen.getByText('2002/03 · 50 sezón')).toBeInTheDocument())
  })

  it('uses actual saved full-simulation summary without fabricating match outcomes', async () => {
    api.getAuthoritativeFullSimulationHistory.mockResolvedValue({
      run_id: runId, branch_id: branchId,
      items: [{ command_id: 'full-a', status: 'complete', completed_season_count: 2, final_completed_week_count: 3 }]
    })
    mount()
    expect(await screen.findByText('Poslední plná simulace')).toBeInTheDocument()
    expect(screen.getByText(/2 dokončených sezón/)).toBeInTheDocument()
    expect(screen.queryByText('Winner')).not.toBeInTheDocument()
  })

  it('displays real future tournaments and published champions from the selected saved revision', async () => {
    api.getRunHomeActivity.mockResolvedValue({
      schema_version: 'run_home_activity.v1', run_id: runId, branch_id: branchId,
      saved_revision_id: 'saved-1', source: 'selected_branch_saved_revision',
      calendar_status: 'ready', result_status: 'ready', ranking_changes_status: 'unsupported',
      total_calendar_events: 2, published_result_count: 1,
      upcoming: [{ event_id: 'EVT-2', event_name: 'Saved Autumn Open', season: '2002/03', season_index: 2, week: 5, category: 'PLATINUM', status: 'planned' }],
      recent_results: [{ event_id: 'EVT-1', event_name: 'Saved Summer Cup', season: '2002/03', season_index: 2, week: 3, category: 'GOLD', status: 'completed', champion_player_id: 'p-real', finalist_player_id: 'p-final' }]
    })
    mount()
    expect(await screen.findByText('Saved Autumn Open')).toBeInTheDocument()
    expect(screen.getByText('Saved Summer Cup')).toBeInTheDocument()
    expect(screen.getByText(/p-real/)).toBeInTheDocument()
    expect(screen.queryByText(/fake champion/i)).not.toBeInTheDocument()
  })

  it('fails closed when returned saved revision belongs to a stale or foreign Branch', async () => {
    api.getRunHomeActivity.mockResolvedValue({
      schema_version: 'run_home_activity.v1', run_id: runId, branch_id: 'foreign',
      saved_revision_id: 'saved-1', source: 'selected_branch_saved_revision',
      calendar_status: 'empty', result_status: 'empty', ranking_changes_status: 'unsupported',
      total_calendar_events: 0, published_result_count: 0, upcoming: [], recent_results: []
    })
    mount()
    expect((await screen.findAllByText('Saved Home activity identity mismatch')).length).toBeGreaterThan(0)
    expect(screen.queryByText('Saved Autumn Open')).not.toBeInTheDocument()
  })

  it('renders saved weekly rank movement with no fabricated entrants climb', async () => {
    api.getRunHomeRankingChanges.mockResolvedValue({
      schema_version: 'run_home_ranking_changes.v1', run_id: runId, branch_id: branchId,
      saved_revision_id: 'saved-1', source: 'selected_branch_saved_revision',
      status: 'ready', previous_week_ordinal: 1, current_week_ordinal: 2,
      current_row_count: 3, total_change_count: 3, moved_count: 1,
      entered_count: 1, exited_count: 0, points_only_count: 1,
      changes: [
        { player_id: 'Player-Up', movement: 'up', previous_rank: 5, current_rank: 2, previous_points: 50, current_points: 65, points_delta: 15, rank_delta: 3 },
        { player_id: 'Player-Entered', movement: 'entered', previous_rank: null, current_rank: 3, previous_points: null, current_points: 20, points_delta: null, rank_delta: null },
        { player_id: 'Player-Points', movement: 'points_only', previous_rank: 1, current_rank: 1, previous_points: 100, current_points: 120, points_delta: 20, rank_delta: 0 },
      ]
    })
    mount()
    expect(await screen.findByText('Player-Up')).toBeInTheDocument()
    expect(screen.getByText('#5 → #2 (+3) · +15 b.')).toBeInTheDocument()
    expect(screen.getByText('Nově v pořadí')).toBeInTheDocument()
    expect(screen.getByText('Stejná pozice · +20 b.')).toBeInTheDocument()
    expect(screen.getByText('2000/01 · W2 → 2000/01 · W3', { exact: false })).toBeInTheDocument()
  })

  it('blocks foreign or stale Saved Revision rank movement', async () => {
    api.getRunHomeRankingChanges.mockResolvedValue({
      schema_version: 'run_home_ranking_changes.v1', run_id: runId, branch_id: branchId,
      saved_revision_id: 'stale-head', source: 'selected_branch_saved_revision',
      status: 'ready', previous_week_ordinal: 1, current_week_ordinal: 2,
      current_row_count: 1, total_change_count: 1, moved_count: 1,
      entered_count: 0, exited_count: 0, points_only_count: 0,
      changes: [{ player_id: 'LEAK', movement: 'up', previous_rank: 10, current_rank: 1, points_delta: 1, rank_delta: 9 }]
    })
    mount()
    expect(await screen.findByText('Saved ranking changes identity mismatch')).toBeInTheDocument()
    expect(screen.queryByText('LEAK')).not.toBeInTheDocument()
  })

  it('renders verified Saved Revision player names and clickable canonical identity details', async () => {
    api.getRunHomeActivity.mockResolvedValue({
      schema_version: 'run_home_activity.v1', run_id: runId, branch_id: branchId,
      saved_revision_id: 'saved-1', source: 'selected_branch_saved_revision',
      calendar_status: 'empty', result_status: 'ready', ranking_changes_status: 'unsupported',
      total_calendar_events: 0, published_result_count: 1, upcoming: [],
      recent_results: [{
        event_id: 'event-1', event_name: 'Real Saved Final', season: '2000/01',
        season_index: 0, week: 2, category: 'GOLD', status: 'completed',
        champion_player_id: 'P1', finalist_player_id: 'P2'
      }]
    })
    api.getSavedHomePlayerIdentities.mockImplementation(async (_r: string, _b: string, ids: string[]) => ({
      schema_version: 'run_home_player_identities.v1', run_id: runId, branch_id: branchId,
      saved_revision_id: 'saved-1', source: 'selected_branch_saved_revision',
      status: 'ready', requested_ids: ids,
      players: ids.map(id => ({
        player_id: id, display_name: id === 'P1' ? 'Verified Champion' : 'Verified Finalist',
        country_code: id === 'P1' ? 'CZE' : 'EGY', identity_source: 'initial_world'
      })), unresolved_ids: [],
    }))
    mount()
    expect(await screen.findByRole('link', { name: /Verified Champion/ })).toHaveAttribute(
      'href', '/admin/runs/' + runId + '/people/P1'
    )
    expect(screen.getByRole('link', { name: /Verified Finalist/ })).toHaveAttribute(
      'href', '/admin/runs/' + runId + '/people/P2'
    )
  })

  it('rejects stale player identity revision without leaking a name or wrong link', async () => {
    api.getRunHomeRankingChanges.mockResolvedValue({
      schema_version: 'run_home_ranking_changes.v1', run_id: runId, branch_id: branchId,
      saved_revision_id: 'saved-1', source: 'selected_branch_saved_revision',
      status: 'ready', previous_week_ordinal: 0, current_week_ordinal: 1,
      current_row_count: 1, total_change_count: 1, moved_count: 1,
      entered_count: 0, exited_count: 0, points_only_count: 0,
      changes: [{
        player_id: 'P1', movement: 'up', previous_rank: 2, current_rank: 1,
        previous_points: 100, current_points: 110, points_delta: 10, rank_delta: 1
      }]
    })
    api.getSavedHomePlayerIdentities.mockImplementation(async (_r: string, _b: string, ids: string[]) => ({
      schema_version: 'run_home_player_identities.v1', run_id: runId, branch_id: branchId,
      saved_revision_id: 'foreign-revision', source: 'selected_branch_saved_revision',
      status: 'ready', requested_ids: ids, players: [{
        player_id: 'P1', display_name: 'WRONG NAME', country_code: 'USA', identity_source: 'initial_world'
      }], unresolved_ids: [],
    }))
    mount()
    expect(await screen.findByText('Saved player identities do not match selected Branch HEAD')).toBeInTheDocument()
    expect(screen.queryByText(/WRONG NAME/)).not.toBeInTheDocument()
    expect(screen.getByText('P1')).toBeInTheDocument()
  })

  it('keeps same-run branches separate and refuses mismatched simulation position', async () => {
    api.getAuthoritativeSimulationPosition.mockResolvedValue(refPosition({ branch_id: 'foreign' }))
    mount()
    expect(await screen.findByText('Simulation position identity mismatch')).toBeInTheDocument()
    expect(screen.queryByText('Hratelné zápasy: 2')).not.toBeInTheDocument()
  })
})
