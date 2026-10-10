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
  getRunContainer: vi.fn(), listRunBranches: vi.fn(), getBranchState: vi.fn(), listBranchCheckpoints: vi.fn(), getRunHomeActivity: vi.fn(),
  getBranchWorkingDraft: vi.fn(), getRunPackageState: vi.fn(), getAuthoritativeSimulationPosition: vi.fn(),
  getPendingAuthoritativeFullSimulations: vi.fn(), getAuthoritativeFullSimulationHistory: vi.fn(), listSavedRevisionHistory: vi.fn()
}))
vi.mock('../api/client', () => api)
vi.mock('../components/RunPackageSetupPanel', () => ({ RunPackageSetupPanel: () => <p>World and Calendar copies</p> }))
vi.mock('../components/RunInitialWorldSetupPanel', () => ({ RunInitialWorldSetupPanel: () => <p>Player setup</p> }))
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
    expect(await screen.findByText('Saved Home activity identity mismatch')).toBeInTheDocument()
    expect(screen.queryByText('Saved Autumn Open')).not.toBeInTheDocument()
  })

  it('keeps same-run branches separate and refuses mismatched simulation position', async () => {
    api.getAuthoritativeSimulationPosition.mockResolvedValue(refPosition({ branch_id: 'foreign' }))
    mount()
    expect(await screen.findByText('Simulation position identity mismatch')).toBeInTheDocument()
    expect(screen.queryByText('Hratelné zápasy: 2')).not.toBeInTheDocument()
  })
})
