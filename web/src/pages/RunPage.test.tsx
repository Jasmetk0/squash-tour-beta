import { fireEvent, screen, waitFor } from '@testing-library/react'
import { useQueryClient } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Link, useParams } from 'react-router-dom'

import { RunPage } from './RunPage'
import { renderWithRoute as renderRoute } from '../test/testUtils'
import { AdminBranchProvider, useAdminBranch } from '../admin/AdminBranchContext'
import { AdminTimeProvider } from '../admin/AdminTimeContext'
import { AdminTimeControl } from '../components/AdminTimeControl'
import { LanguageProvider } from '../i18n/LanguageContext'
import { runHomeReadinessFixture } from '../test/runHomeReadinessFixture'
import type { RunHomeReadiness } from '../api/runHomeReadiness'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) { super(message); this.status = status }
  },
  getRunContainer: vi.fn(), listRunBranches: vi.fn(), getBranchState: vi.fn(), listBranchCheckpoints: vi.fn(), getRunHomeActivity: vi.fn(), getRunHomeReadiness: vi.fn(), getRunHomeRankingChanges: vi.fn(), getSavedHomePlayerIdentities: vi.fn(),
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
function mountWithFeedRefresh(queryKey: string) {
  function RefreshSavedFeed(): JSX.Element {
    const client = useQueryClient()
    return <button type="button" onClick={() => {
      void client.invalidateQueries({ queryKey: [queryKey, runId, branchId] })
    }}>Refetch saved feed</button>
  }
  return renderRoute(
    <LanguageProvider><AdminBranchProvider runId={runId}><AdminTimeProvider>
      <RefreshSavedFeed/><RunPage/>
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
function savedReadiness(draftVersion = 1): RunHomeReadiness {
  const codes = ['world', 'calendar_package', 'population', 'health',
    'official_ranking', 'working_draft'] as const
  const items: RunHomeReadiness['items'] = codes.map(code => ({
    code, status: code === 'health' ? 'optional' : code === 'working_draft' ? 'saved' : 'missing',
    evidence_count: 0
  }))
  return runHomeReadinessFixture(runId, branchId, {
    saved_revision_id: 'saved-1', draft_version: draftVersion,
    current_calendar: {
      schema_version: 'run_calendar.v1', weeks_per_year: 61,
      season_start_year_week: 37, start_year: 2000, season_count: 50
    },
    items, sporting_calendar_supported_by_legacy_writers: true
  })
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
    api.getRunHomeReadiness.mockResolvedValue(savedReadiness())
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
    api.listSavedRevisionHistory.mockResolvedValue({ run_id: runId, branch_id: branchId, saved_head_revision_id: 'saved-1', saved_revisions: [{
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


  it('rejects foreign Run package state without calling it a legitimately empty Run', async () => {
    api.getRunPackageState.mockResolvedValue({
      state: { run_id: 'foreign-run', branch_id: branchId, players: ['LEAK'] },
      fingerprint: 'foreign'
    })
    api.getAuthoritativeSimulationPosition.mockRejectedValue(new api.ApiError('Not positioned', 404))
    mount()
    expect((await screen.findAllByText('Uložené balíčky neodpovídají vybranému Runu a Branchi.')).length)
      .toBeGreaterThan(0)
    expect(screen.queryByText(/Prázdný Run je platný/)).toBeNull()
    expect(screen.queryByText(/Načtená data nehlásí žádný aktuální blokátor/)).toBeNull()
  })

  it('rejects a response missing its package-state envelope instead of treating it as empty', async () => {
    api.getRunPackageState.mockResolvedValue({ fingerprint: 'unverified' })
    api.getAuthoritativeSimulationPosition.mockRejectedValue(new api.ApiError('Not positioned', 404))
    mount()
    expect((await screen.findAllByText('Uložené balíčky neodpovídají vybranému Runu a Branchi.')).length)
      .toBeGreaterThan(0)
    expect(screen.queryByText(/Prázdný Run je platný/)).toBeNull()
  })

  it('re-fetches Branch package evidence when the selected Saved Revision HEAD changes', async () => {
    api.getAuthoritativeSimulationPosition.mockRejectedValue(new api.ApiError('Not positioned', 404))
    const initialBranch = {
      run_id: runId, branch_id: branchId, display_name: 'Timeline 1', status: 'active',
      saved_head_revision_id: 'saved-1', head_checkpoint_id: 'cp-current',
      read_only: false, is_official: true
    }
    api.listRunBranches.mockResolvedValueOnce({ run_branches: [initialBranch] })
      .mockResolvedValue({ run_branches: [{ ...initialBranch, saved_head_revision_id: 'saved-2' }] })
    let finishNewHead!: (value: unknown) => void
    api.getRunPackageState.mockResolvedValueOnce({ state: null, fingerprint: null })
      .mockImplementationOnce(() => new Promise(done => { finishNewHead = done }))
    function ReloadSavedHead(): JSX.Element {
      const client = useQueryClient()
      return <button type="button" onClick={() => {
        void client.invalidateQueries({ queryKey: ['admin-run-branches', runId] })
      }}>Reload saved HEAD</button>
    }
    renderRoute(
      <LanguageProvider><AdminBranchProvider runId={runId}><AdminTimeProvider>
        <ReloadSavedHead /><RunPage />
      </AdminTimeProvider></AdminBranchProvider></LanguageProvider>,
      '/admin/runs/' + runId
    )
    expect(await screen.findByText(/Prázdný Run je platný/)).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Reload saved HEAD' }))
    await waitFor(() => expect(api.getRunPackageState).toHaveBeenCalledTimes(2))
    expect(screen.queryByText(/Prázdný Run je platný/)).toBeNull()
    finishNewHead({
      state: { run_id: runId, branch_id: branchId, world_package: { count: 1 } },
      fingerprint: 'saved-2-fingerprint'
    })
    expect(await screen.findByText('Branch zatím nemá uloženou pozici simulace.')).toBeVisible()
    expect(screen.queryByText(/Prázdný Run je platný/)).toBeNull()
    expect(screen.queryByText(/Uložené balíčky neodpovídají vybranému Runu a Branchi/)).toBeNull()
  })

  it('rejects a stale Saved history HEAD instead of exposing its revisions as current', async () => {
    api.listSavedRevisionHistory.mockResolvedValue({
      run_id: runId, branch_id: branchId, saved_head_revision_id: 'old-head',
      saved_revisions: [{ revision_id: 'old-revision', kind: 'LEAKED OLD REVISION',
        sequence: 2, created_at: '2026-10-01' }]
    })
    mount()
    expect((await screen.findAllByText('Historie uložených revizí neodpovídá vybranému Runu, Branchi nebo Saved HEAD.')).length)
      .toBeGreaterThan(0)
    expect(screen.queryByText('LEAKED OLD REVISION')).toBeNull()
    expect(screen.queryByText(/Načtená data nehlásí žádný aktuální blokátor/)).toBeNull()
  })

  it('reads a fresh Saved history when Branch HEAD changes rather than showing the old list', async () => {
    const initialBranch = {
      run_id: runId, branch_id: branchId, display_name: 'Timeline 1', status: 'active',
      saved_head_revision_id: 'saved-1', head_checkpoint_id: 'cp-current',
      read_only: false, is_official: true
    }
    api.listRunBranches.mockResolvedValueOnce({ run_branches: [initialBranch] })
      .mockResolvedValue({ run_branches: [{ ...initialBranch, saved_head_revision_id: 'saved-2' }] })
    let finishHistory!: (value: unknown) => void
    api.listSavedRevisionHistory.mockResolvedValueOnce({
      run_id: runId, branch_id: branchId, saved_head_revision_id: 'saved-1',
      saved_revisions: [{ revision_id: 'r-old', kind: 'old-history-kind',
        sequence: 1, created_at: '2026-10-01' }]
    }).mockImplementationOnce(() => new Promise(done => { finishHistory = done }))
    function ReloadHead(): JSX.Element {
      const client = useQueryClient()
      return <button type="button" onClick={() => {
        void client.invalidateQueries({ queryKey: ['admin-run-branches', runId] })
      }}>Reload saved history HEAD</button>
    }
    renderRoute(
      <LanguageProvider><AdminBranchProvider runId={runId}><AdminTimeProvider>
        <ReloadHead /><RunPage />
      </AdminTimeProvider></AdminBranchProvider></LanguageProvider>,
      '/admin/runs/' + runId
    )
    expect(await screen.findByText('old-history-kind')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Reload saved history HEAD' }))
    await waitFor(() => expect(api.listSavedRevisionHistory).toHaveBeenCalledTimes(2))
    expect(screen.queryByText('old-history-kind')).toBeNull()
    finishHistory({
      run_id: runId, branch_id: branchId, saved_head_revision_id: 'saved-2',
      saved_revisions: [{ revision_id: 'r-new', kind: 'new-history-kind',
        sequence: 2, created_at: '2026-10-28' }]
    })
    expect(await screen.findByText('new-history-kind')).toBeVisible()
    expect(screen.queryByText('old-history-kind')).toBeNull()
    expect(screen.queryByText(/Historie uložených revizí neodpovídá vybranému Runu, Branchi/)).toBeNull()
  })

  it('hides prior Saved tournament events during an HTTP refresh and after its failure', async () => {
    const activity = {
      schema_version: 'run_home_activity.v1', run_id: runId, branch_id: branchId,
      saved_revision_id: 'saved-1', source: 'selected_branch_saved_revision',
      calendar_status: 'empty', result_status: 'ready', ranking_changes_status: 'unsupported',
      total_calendar_events: 0, published_result_count: 1, upcoming: [],
      recent_results: [{
        event_id: 'event-1', event_name: 'Old saved final', season: '2000/01',
        season_index: 0, week: 2, category: 'GOLD', status: 'completed',
        champion_player_id: 'P1', finalist_player_id: 'P2'
      }]
    }
    let failRefresh!: (reason: Error) => void
    api.getRunHomeActivity.mockResolvedValueOnce(activity)
      .mockImplementationOnce(() => new Promise((_resolve, reject) => { failRefresh = reject }))
      .mockResolvedValueOnce({ ...activity,
        recent_results: [{ ...activity.recent_results[0], event_name: 'New saved final' }] })
    mountWithFeedRefresh('run-home-activity')
    expect(await screen.findByText('Old saved final')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Refetch saved feed' }))
    await waitFor(() => expect(api.getRunHomeActivity).toHaveBeenCalledTimes(2))
    expect(screen.queryByText('Old saved final')).toBeNull()
    failRefresh(new Error('activity refresh failed'))
    expect((await screen.findAllByText(/activity refresh failed/)).length).toBeGreaterThan(0)
    expect(screen.queryByText('Old saved final')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Refetch saved feed' }))
    expect(await screen.findByText('New saved final')).toBeVisible()
    expect(screen.queryByText('Old saved final')).toBeNull()
  })

  it('does not display cached ranking movements while Saved ranking refresh is pending or failed', async () => {
    const ranking = {
      schema_version: 'run_home_ranking_changes.v1', run_id: runId, branch_id: branchId,
      saved_revision_id: 'saved-1', source: 'selected_branch_saved_revision',
      status: 'ready', previous_week_ordinal: 1, current_week_ordinal: 2,
      current_row_count: 1, total_change_count: 1, moved_count: 1,
      entered_count: 0, exited_count: 0, points_only_count: 0,
      changes: [{
        player_id: 'OLD-RANKING-PLAYER', movement: 'up',
        previous_rank: 9, current_rank: 1, previous_points: 5, current_points: 100,
        points_delta: 95, rank_delta: 8
      }]
    }
    let failRefresh!: (reason: Error) => void
    api.getRunHomeRankingChanges.mockResolvedValueOnce(ranking)
      .mockImplementationOnce(() => new Promise((_resolve, reject) => { failRefresh = reject }))
      .mockResolvedValueOnce({ ...ranking, changes: [{
        ...ranking.changes[0], player_id: 'NEW-RANKING-PLAYER'
      }] })
    mountWithFeedRefresh('run-home-ranking-changes')
    expect(await screen.findByText('OLD-RANKING-PLAYER')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Refetch saved feed' }))
    await waitFor(() => expect(api.getRunHomeRankingChanges).toHaveBeenCalledTimes(2))
    expect(screen.queryByText('OLD-RANKING-PLAYER')).toBeNull()
    failRefresh(new Error('ranking refresh failed'))
    expect((await screen.findAllByText(/ranking refresh failed/)).length).toBeGreaterThan(0)
    expect(screen.queryByText('OLD-RANKING-PLAYER')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Refetch saved feed' }))
    expect(await screen.findByText('NEW-RANKING-PLAYER')).toBeVisible()
    expect(screen.queryByText('OLD-RANKING-PLAYER')).toBeNull()
  })

  it('removes cached saved player names while identity lookup refresh is pending or fails', async () => {
    api.getRunHomeActivity.mockResolvedValue({
      schema_version: 'run_home_activity.v1', run_id: runId, branch_id: branchId,
      saved_revision_id: 'saved-1', source: 'selected_branch_saved_revision',
      calendar_status: 'empty', result_status: 'ready', ranking_changes_status: 'unsupported',
      total_calendar_events: 0, published_result_count: 1, upcoming: [],
      recent_results: [{
        event_id: 'event-1', event_name: 'Saved player final', season: '2000/01',
        season_index: 0, week: 2, category: 'GOLD', status: 'completed',
        champion_player_id: 'P1', finalist_player_id: 'P2'
      }]
    })
    const identity = (displayName: string) => ({
      schema_version: 'run_home_player_identities.v1', run_id: runId, branch_id: branchId,
      saved_revision_id: 'saved-1', source: 'selected_branch_saved_revision',
      status: 'ready', requested_ids: ['P1', 'P2'],
      players: [
        { player_id: 'P1', display_name: displayName, country_code: 'CZE', identity_source: 'initial_world' },
        { player_id: 'P2', display_name: 'Other verified player', country_code: 'EGY', identity_source: 'initial_world' }
      ], unresolved_ids: []
    })
    let failRefresh!: (reason: Error) => void
    api.getSavedHomePlayerIdentities.mockResolvedValueOnce(identity('Old verified name'))
      .mockImplementationOnce(() => new Promise((_resolve, reject) => { failRefresh = reject }))
      .mockResolvedValueOnce(identity('New verified name'))
    mountWithFeedRefresh('run-home-player-identities')
    expect(await screen.findByRole('link', { name: /Old verified name/ })).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Refetch saved feed' }))
    await waitFor(() => expect(api.getSavedHomePlayerIdentities).toHaveBeenCalledTimes(2))
    expect(screen.queryByText(/Old verified name/)).toBeNull()
    expect(screen.getByText('P1')).toBeInTheDocument()
    failRefresh(new Error('identity refresh failed'))
    expect((await screen.findAllByText(/identity refresh failed/)).length).toBeGreaterThan(0)
    expect(screen.queryByText(/Old verified name/)).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Refetch saved feed' }))
    expect(await screen.findByRole('link', { name: /New verified name/ })).toBeVisible()
    expect(screen.queryByText(/Old verified name/)).toBeNull()
  })

  it('hides stale simulation position during and after a failed refresh, then recovers', async () => {
    let rejectRefresh!: (reason: Error) => void
    api.getAuthoritativeSimulationPosition.mockResolvedValueOnce(refPosition())
      .mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectRefresh = reject }))
      .mockResolvedValueOnce(refPosition({ eligible_match_ids: ['m1'] }))
    mountWithFeedRefresh('authoritative-simulation-position')
    expect(await screen.findByText('Hratelné zápasy: 2')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Refetch saved feed' }))
    await waitFor(() => expect(api.getAuthoritativeSimulationPosition).toHaveBeenCalledTimes(2))
    expect(screen.queryByText('Hratelné zápasy: 2')).toBeNull()
    expect(screen.queryByText(/Načtená data nehlásí žádný aktuální blokátor/)).toBeNull()
    rejectRefresh(new Error('position refresh unavailable'))
    expect((await screen.findAllByText(/position refresh unavailable/)).length).toBeGreaterThan(0)
    expect(screen.queryByText('Hratelné zápasy: 2')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Refetch saved feed' }))
    expect(await screen.findByText('Hratelné zápasy: 1')).toBeVisible()
    expect(screen.queryByText('Hratelné zápasy: 2')).toBeNull()
  })

  it('hides stale pending simulation count until a fresh successful Branch response arrives', async () => {
    let rejectRefresh!: (reason: Error) => void
    api.getPendingAuthoritativeFullSimulations.mockResolvedValueOnce({
      run_id: runId, branch_id: branchId, operations: [{ command_id: 'a' }, { command_id: 'b' }]
    }).mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectRefresh = reject }))
      .mockResolvedValueOnce({ run_id: runId, branch_id: branchId, operations: [] })
    mountWithFeedRefresh('authoritative-pending-full-simulations')
    expect((await screen.findAllByText(/Pozastavené\/čekající plné simulace/)).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: 'Refetch saved feed' }))
    await waitFor(() => expect(api.getPendingAuthoritativeFullSimulations).toHaveBeenCalledTimes(2))
    expect(screen.queryAllByText(/Pozastavené\/čekající plné simulace:/)).toHaveLength(0)
    expect(screen.queryByText(/Načtená data nehlásí žádný aktuální blokátor/)).toBeNull()
    rejectRefresh(new Error('pending operations refresh failed'))
    expect((await screen.findAllByText(/pending operations refresh failed/)).length).toBeGreaterThan(0)
    expect(screen.queryAllByText(/Pozastavené\/čekající plné simulace:/)).toHaveLength(0)
    fireEvent.click(screen.getByRole('button', { name: 'Refetch saved feed' }))
    await waitFor(() => expect(api.getPendingAuthoritativeFullSimulations).toHaveBeenCalledTimes(3))
    expect(screen.queryAllByText(/Pozastavené\/čekající plné simulace:/)).toHaveLength(0)
  })

  it('hides stale latest Full Simulation history during refresh and after error', async () => {
    const history = (count: number) => ({
      run_id: runId, branch_id: branchId,
      items: [{
        command_id: 'full-sim', status: 'complete',
        completed_season_count: count, final_completed_week_count: count
      }]
    })
    let rejectRefresh!: (reason: Error) => void
    api.getAuthoritativeFullSimulationHistory.mockResolvedValueOnce(history(2))
      .mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectRefresh = reject }))
      .mockResolvedValueOnce(history(3))
    mountWithFeedRefresh('authoritative-full-simulation-history')
    expect(await screen.findByText(/2 dokončených sezón/)).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Refetch saved feed' }))
    await waitFor(() => expect(api.getAuthoritativeFullSimulationHistory).toHaveBeenCalledTimes(2))
    expect(screen.queryByText(/2 dokončených sezón/)).toBeNull()
    rejectRefresh(new Error('full simulation history refresh failed'))
    expect((await screen.findAllByText(/full simulation history refresh failed/)).length).toBeGreaterThan(0)
    expect(screen.queryByText(/2 dokončených sezón/)).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Refetch saved feed' }))
    expect(await screen.findByText(/3 dokončených sezón/)).toBeVisible()
    expect(screen.queryByText(/2 dokončených sezón/)).toBeNull()
  })

  it('re-reads every simulation inspection after Saved HEAD changes, hiding earlier slot evidence', async () => {
    const initial = {
      run_id: runId, branch_id: branchId, display_name: 'Timeline 1',
      status: 'active', saved_head_revision_id: 'saved-1',
      head_checkpoint_id: 'cp-current', read_only: false, is_official: true
    }
    api.listRunBranches.mockResolvedValueOnce({ run_branches: [initial] })
      .mockResolvedValue({ run_branches: [{ ...initial, saved_head_revision_id: 'saved-2' }] })
    let resolveNewPosition!: (result: unknown) => void
    api.getAuthoritativeSimulationPosition.mockResolvedValueOnce(refPosition())
      .mockImplementationOnce(() => new Promise(done => { resolveNewPosition = done }))
    function ReloadHead(): JSX.Element {
      const client = useQueryClient()
      return <button type="button" onClick={() => {
        void client.invalidateQueries({ queryKey: ['admin-run-branches', runId] })
      }}>Reload simulation HEAD</button>
    }
    renderRoute(
      <LanguageProvider><AdminBranchProvider runId={runId}><AdminTimeProvider>
        <ReloadHead /><RunPage />
      </AdminTimeProvider></AdminBranchProvider></LanguageProvider>,
      '/admin/runs/' + runId
    )
    expect(await screen.findByText('Hratelné zápasy: 2')).toBeVisible()
    await waitFor(() => {
      expect(api.getPendingAuthoritativeFullSimulations).toHaveBeenCalledTimes(1)
      expect(api.getAuthoritativeFullSimulationHistory).toHaveBeenCalledTimes(1)
    })
    fireEvent.click(screen.getByRole('button', { name: 'Reload simulation HEAD' }))
    await waitFor(() => {
      expect(api.getAuthoritativeSimulationPosition).toHaveBeenCalledTimes(2)
      expect(api.getPendingAuthoritativeFullSimulations).toHaveBeenCalledTimes(2)
      expect(api.getAuthoritativeFullSimulationHistory).toHaveBeenCalledTimes(2)
    })
    expect(screen.queryByText('Hratelné zápasy: 2')).toBeNull()
    resolveNewPosition(refPosition({ eligible_match_ids: ['new-match'] }))
    expect(await screen.findByText('Hratelné zápasy: 1')).toBeVisible()
    expect(screen.queryByText('Hratelné zápasy: 2')).toBeNull()
  })

  it('does not count foreign pending operations or foreign Full Simulation history as this Branch', async () => {
    api.getPendingAuthoritativeFullSimulations.mockResolvedValue({
      run_id: runId, branch_id: 'other-branch',
      operations: [{ command_id: 'foreign-operation' }]
    })
    api.getAuthoritativeFullSimulationHistory.mockResolvedValue({
      run_id: 'other-run', branch_id: branchId,
      items: [{ command_id: 'foreign-history', status: 'complete',
        completed_season_count: 5, final_completed_week_count: 5 }]
    })
    mount()
    expect((await screen.findAllByText('Pending Full Simulation identity mismatch')).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('Full Simulation history identity mismatch')).length).toBeGreaterThan(0)
    expect(screen.queryByText(/5 dokončených sezón/)).toBeNull()
    expect(screen.queryAllByText(/Pozastavené\/čekající plné simulace:/)).toHaveLength(0)
    expect(screen.queryByText(/Načtená data nehlásí žádný aktuální blokátor/)).toBeNull()
  })

  it('describes a Branch without a Saved HEAD instead of endlessly loading readiness', async () => {
    api.listRunBranches.mockResolvedValueOnce({ run_branches: [{
      run_id: runId, branch_id: branchId, display_name: 'Timeline 1',
      status: 'active', saved_head_revision_id: null,
      head_checkpoint_id: 'cp-current', read_only: false, is_official: true
    }] })
    mount()
    expect(await screen.findByText(/nemá ověřenou Saved Revision HEAD/)).toBeVisible()
    expect(screen.queryByRole('region', { name: 'Připravenost Runu' })).toBeNull()
    expect(screen.queryByRole('region', { name: 'Obnova kontroly podkladů Runu' })).toBeNull()
    expect(api.getRunHomeReadiness).not.toHaveBeenCalled()
  })

  it('keeps Saved-readiness recovery out of the historical checkpoint view', async () => {
    api.getRunHomeReadiness.mockRejectedValue(new Error('saved readiness offline'))
    mount()
    await screen.findByRole('option', { name: /#1/ })
    fireEvent.change(screen.getByRole('combobox', { name: 'Admin Time context' }), {
      target: { value: 'cp-past' }
    })
    expect(await screen.findByText(/Historické výsledky a stavy/)).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Znovu ověřit uložené podklady' })).toBeNull()
    expect(screen.queryByText(/Kontrolu připravenosti nelze ověřit/)).toBeNull()
  })

  it('does not present Saved readiness without a verified matching Working Draft', async () => {
    api.getBranchWorkingDraft.mockRejectedValueOnce(new Error('draft unavailable'))
      .mockResolvedValueOnce({
        run_id: runId, branch_id: branchId, draft_version: 1,
        status: 'clean', change_count: 0
      })
    mount()
    expect(await screen.findByRole('region', { name: 'Obnova kontroly podkladů Runu' })).toBeVisible()
    expect(screen.queryByRole('region', { name: 'Připravenost Runu' })).toBeNull()
    expect(screen.getByText(/draft unavailable/)).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Znovu ověřit uložené podklady' }))
    expect(await screen.findByRole('region', { name: 'Připravenost Runu' })).toBeVisible()
    expect(api.getBranchWorkingDraft).toHaveBeenCalledTimes(2)
    expect(api.getRunHomeReadiness).toHaveBeenCalledTimes(2)
  })

  it('rejects a malformed Run calendar even when the Saved-readiness DTO is valid', async () => {
    api.getRunContainer.mockResolvedValueOnce({
      run_id: runId, display_name: 'Demo Run', storage_kind: 'custom_local', read_only: false,
      metadata_json: { run_calendar: { schema_version: 'bad-calendar' } }
    }).mockResolvedValueOnce({
      run_id: runId, display_name: 'Demo Run', storage_kind: 'custom_local', read_only: false
    })
    mount()
    expect(await screen.findByRole('region', { name: 'Obnova kontroly podkladů Runu' })).toBeVisible()
    expect(screen.queryByRole('region', { name: 'Připravenost Runu' })).toBeNull()
    expect(screen.getByText(/Kalendář Runu není dostupný/)).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Znovu ověřit uložené podklady' }))
    expect(await screen.findByRole('region', { name: 'Připravenost Runu' })).toBeVisible()
    expect(api.getRunContainer.mock.calls.length).toBeGreaterThanOrEqual(2)
    expect(api.getRunContainer).toHaveBeenCalledWith(runId)
  })

  it('does not bypass a foreign Working Draft identity in a successful HTTP response', async () => {
    api.getBranchWorkingDraft.mockResolvedValueOnce({
      run_id: runId, branch_id: 'other-branch', draft_version: 1,
      status: 'clean', change_count: 0
    }).mockResolvedValueOnce({
      run_id: runId, branch_id: branchId, draft_version: 1,
      status: 'clean', change_count: 0
    })
    mount()
    expect(await screen.findByRole('region', { name: 'Obnova kontroly podkladů Runu' })).toBeVisible()
    expect(screen.queryByRole('region', { name: 'Připravenost Runu' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Znovu ověřit uložené podklady' }))
    expect(await screen.findByRole('region', { name: 'Připravenost Runu' })).toBeVisible()
  })

  it('refreshes Run clock, Working Draft and Saved evidence together from the checklist button', async () => {
    mount()
    expect(await screen.findByRole('region', { name: 'Připravenost Runu' })).toBeVisible()
    const beforeRun = api.getRunContainer.mock.calls.length
    const beforeDraft = api.getBranchWorkingDraft.mock.calls.length
    const beforeReadiness = api.getRunHomeReadiness.mock.calls.length
    let resumeDraft!: (value: unknown) => void
    api.getBranchWorkingDraft.mockImplementationOnce(() => new Promise(done => { resumeDraft = done }))
    fireEvent.click(screen.getByRole('button', { name: 'Obnovit kontrolu' }))
    await waitFor(() => expect(api.getBranchWorkingDraft).toHaveBeenCalledTimes(beforeDraft + 1))
    expect(api.getRunContainer.mock.calls.length).toBeGreaterThan(beforeRun)
    expect(api.getRunHomeReadiness).toHaveBeenCalledTimes(beforeReadiness + 1)
    expect(screen.queryByRole('region', { name: 'Připravenost Runu' })).toBeNull()
    expect(screen.getByText('Ověřuji aktuální uložené podklady vybrané branche…')).toBeVisible()
    resumeDraft({ run_id: runId, branch_id: branchId, draft_version: 1,
      status: 'clean', change_count: 0 })
    expect(await screen.findByRole('region', { name: 'Připravenost Runu' })).toBeVisible()
  })

  it('never renders delayed Saved evidence from the previous Branch after switching', async () => {
    const second = 'branch-second'
    api.listRunBranches.mockResolvedValue({ run_branches: [
      { run_id: runId, branch_id: branchId, display_name: 'Timeline A',
        status: 'active', saved_head_revision_id: 'saved-1',
        head_checkpoint_id: 'cp-current', read_only: false, is_official: true },
      { run_id: runId, branch_id: second, display_name: 'Timeline B',
        status: 'active', saved_head_revision_id: 'saved-2',
        head_checkpoint_id: null, read_only: false, is_official: false }
    ] })
    api.getBranchWorkingDraft.mockImplementation(async (_run: string, branch: string) => ({
      run_id: runId, branch_id: branch, draft_version: 1, status: 'clean', change_count: 0
    }))
    let completeFirst!: (value: unknown) => void
    const secondEvidence = {
      ...savedReadiness(), branch_id: second, saved_revision_id: 'saved-2',
      items: savedReadiness().items.map(item => item.code === 'world'
        ? { ...item, status: 'saved' as const, evidence_count: 7 } : item)
    }
    api.getRunHomeReadiness.mockImplementation((_run: string, branch: string) =>
      branch === second ? Promise.resolve(secondEvidence)
        : new Promise(done => { completeFirst = done }))
    function BranchSwitch(): JSX.Element {
      const { selectBranch } = useAdminBranch()
      return <button type="button" onClick={() => { selectBranch(second) }}>
        Select Timeline B
      </button>
    }
    renderRoute(
      <LanguageProvider><AdminBranchProvider runId={runId}><AdminTimeProvider>
        <BranchSwitch /><RunPage />
      </AdminTimeProvider></AdminBranchProvider></LanguageProvider>,
      '/admin/runs/' + runId
    )
    await waitFor(() => expect(api.getRunHomeReadiness).toHaveBeenCalledWith(runId, branchId))
    fireEvent.click(screen.getByRole('button', { name: 'Select Timeline B' }))
    expect(await screen.findByText('Timeline B')).toBeVisible()
    expect(await screen.findByRole('region', { name: 'Připravenost Runu' })).toBeVisible()
    expect(screen.getByText(/Entity World Package: 7/)).toBeInTheDocument()
    completeFirst({
      ...savedReadiness(),
      items: savedReadiness().items.map(item => item.code === 'world'
        ? { ...item, status: 'saved' as const, evidence_count: 13 } : item)
    })
    await waitFor(() => expect(api.getRunHomeReadiness).toHaveBeenCalledWith(runId, second))
    expect(screen.getByText(/Entity World Package: 7/)).toBeInTheDocument()
    expect(screen.queryByText(/Entity World Package: 13/)).toBeNull()
    expect(screen.queryByText('Saved readiness identity/HEAD/draft/calendar differs from selected Run.')).toBeNull()
  })

  it('does not let a delayed old Run readiness response overwrite the newly opened Run', async () => {
    const otherRun = 'second-run'
    const otherBranch = 'branch-of-second-run'
    api.getRunContainer.mockImplementation(async (requestedRun: string) => ({
      run_id: requestedRun, display_name: requestedRun === otherRun ? 'Second Run' : 'First Run',
      storage_kind: 'custom_local', read_only: false, status: 'working',
      official_branch_id: requestedRun === otherRun ? otherBranch : branchId
    }))
    api.listRunBranches.mockImplementation(async (requestedRun: string) => ({
      run_branches: [{
        run_id: requestedRun, branch_id: requestedRun === otherRun ? otherBranch : branchId,
        display_name: 'Timeline 1', status: 'active', read_only: false,
        saved_head_revision_id: requestedRun === otherRun ? 'second-head' : 'saved-1',
        head_checkpoint_id: null, is_official: true
      }]
    }))
    api.getBranchWorkingDraft.mockImplementation(async (requestedRun: string, requestedBranch: string) => ({
      run_id: requestedRun, branch_id: requestedBranch, status: 'clean',
      change_count: 0, draft_version: 1
    }))
    let resolveFirst!: (value: unknown) => void
    api.getRunHomeReadiness.mockImplementation((requestedRun: string) =>
      requestedRun === otherRun ? Promise.resolve({
        ...savedReadiness(), run_id: otherRun, branch_id: otherBranch,
        saved_revision_id: 'second-head',
        items: savedReadiness().items.map(item => item.code === 'world'
          ? { ...item, status: 'saved' as const, evidence_count: 9 } : item)
      }) : new Promise(done => { resolveFirst = done }))
    function RoutedHome(): JSX.Element {
      const { runId: activeRun = '' } = useParams()
      return <AdminBranchProvider key={activeRun} runId={activeRun}><AdminTimeProvider>
        <Link to={'/admin/runs/' + otherRun}>Open Second Run</Link>
        <RunPage />
      </AdminTimeProvider></AdminBranchProvider>
    }
    renderRoute(<LanguageProvider><RoutedHome /></LanguageProvider>, '/admin/runs/' + runId)
    await waitFor(() => expect(api.getRunHomeReadiness).toHaveBeenCalledWith(runId, branchId))
    fireEvent.click(screen.getByRole('link', { name: 'Open Second Run' }))
    expect(await screen.findByText('Second Run')).toBeVisible()
    expect(await screen.findByRole('region', { name: 'Připravenost Runu' })).toBeVisible()
    expect(screen.getByText(/Entity World Package: 9/)).toBeInTheDocument()
    resolveFirst({
      ...savedReadiness(),
      items: savedReadiness().items.map(item => item.code === 'world'
        ? { ...item, status: 'saved' as const, evidence_count: 13 } : item)
    })
    await waitFor(() => expect(api.getRunHomeReadiness).toHaveBeenCalledWith(otherRun, otherBranch))
    expect(screen.getByText(/Entity World Package: 9/)).toBeInTheDocument()
    expect(screen.queryByText(/Entity World Package: 13/)).toBeNull()
    expect(screen.queryByText('Saved readiness identity/HEAD/draft/calendar differs from selected Run.')).toBeNull()
  })

  it('does not claim readiness during a failed fresh read, and recovers by explicit read-only retry', async () => {
    api.getRunHomeReadiness.mockRejectedValueOnce(new Error('saved readiness offline'))
      .mockResolvedValueOnce(savedReadiness())
    mount()
    expect(await screen.findByRole('region', { name: 'Obnova kontroly podkladů Runu' }))
      .toBeInTheDocument()
    expect(screen.getByText(/Kontrolu připravenosti nelze ověřit/)).toBeVisible()
    expect(screen.queryByRole('region', { name: 'Připravenost Runu' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Znovu ověřit uložené podklady' }))
    expect(await screen.findByRole('region', { name: 'Připravenost Runu' })).toBeVisible()
    expect(screen.queryByRole('region', { name: 'Obnova kontroly podkladů Runu' })).toBeNull()
    expect(api.getRunHomeReadiness).toHaveBeenCalledTimes(2)
  })

  it('rejects a mismatched Saved HEAD readiness response until a matching refetch arrives', async () => {
    api.getRunHomeReadiness.mockResolvedValueOnce({
      ...savedReadiness(), saved_revision_id: 'foreign-head'
    }).mockResolvedValueOnce(savedReadiness())
    mount()
    const recovery = await screen.findByRole('region', { name: 'Obnova kontroly podkladů Runu' })
    expect(recovery).toBeVisible()
    expect(screen.queryByRole('region', { name: 'Připravenost Runu' })).toBeNull()
    expect(screen.getByText('Saved readiness identity/HEAD/draft/calendar differs from selected Run.')).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Znovu ověřit uložené podklady' }))
    expect(await screen.findByRole('region', { name: 'Připravenost Runu' })).toBeVisible()
  })

  it('hides formerly verified readiness while refreshing and after a failed refresh', async () => {
    let rejectRefresh!: (reason: Error) => void
    api.getRunHomeReadiness.mockResolvedValueOnce(savedReadiness())
      .mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectRefresh = reject }))
      .mockResolvedValueOnce(savedReadiness())
    mount()
    expect(await screen.findByRole('region', { name: 'Připravenost Runu' })).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Obnovit kontrolu' }))
    expect(await screen.findByText('Ověřuji aktuální uložené podklady vybrané branche…')).toBeVisible()
    expect(screen.queryByRole('region', { name: 'Připravenost Runu' })).toBeNull()
    rejectRefresh(new Error('network lost on refresh'))
    expect(await screen.findByRole('region', { name: 'Obnova kontroly podkladů Runu' })).toBeVisible()
    expect(screen.queryByRole('region', { name: 'Připravenost Runu' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Znovu ověřit uložené podklady' }))
    expect(await screen.findByRole('region', { name: 'Připravenost Runu' })).toBeVisible()
    expect(api.getRunHomeReadiness).toHaveBeenCalledTimes(3)
  })

  it('keeps custom calendar planning honest instead of offering legacy year-2000 sporting setup', async () => {
    api.getRunContainer.mockResolvedValueOnce({
      run_id:runId, display_name:'Earth planning', storage_kind:'custom_local', read_only:false,
      metadata_json:{run_calendar:{schema_version:'run_calendar.v1',weeks_per_year:52,
        season_start_year_week:35,start_year:2030,season_count:3}}
    })
    mount()
    expect(await screen.findByText(/Nativní operace u jiných kalendářů se ověřují samostatně/)).toBeVisible()
    expect(screen.getByRole('region', { name: 'Příprava obsahu Runu' })).toBeInTheDocument()
    expect(screen.getByText('World and Calendar copies')).toBeVisible()
    expect(screen.queryByText('Ranking setup')).toBeNull()
    expect(screen.queryByText('First tournament setup')).toBeNull()
  })

})
