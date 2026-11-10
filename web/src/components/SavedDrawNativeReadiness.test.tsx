import { render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SavedDrawNativeReadiness } from './SavedDrawNativeReadiness'

// Component contract tests: the API boundary is mocked, not the production HTTP/SQLite stack.
const api = vi.hoisted(() => ({
  getSavedDrawNativePreflight: vi.fn(), getSavedDrawEntryEvidence: vi.fn()
}))
vi.mock('../api/client', () => ({
  ...api,
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status = 500) { super(message); this.status = status }
  }
}))

const a = 'a'.repeat(64)
const b = 'b'.repeat(64)
const preflight = (patch = {}) => ({
  saved_revision_id: 'rev-1', source_plan_fingerprint: a, draw_fingerprint: b,
  ranking_status: 'ranked', point_table_status: 'incomplete',
  required_point_stages: ['W', 'F'], missing_point_stages: ['F'], invalid_point_stages: [],
  native_execution_status: 'ranked_points_incomplete', ...patch
})
const trigger = (player: string, event: string, kind = 'valid_tournament_application') => ({
  schema_version: 'player_tour_entry_trigger.v1', run_id: 'run-a', branch_id: 'branch-a',
  player_id: player, event_id: event, trigger_kind: kind,
  trigger_week: { season_index: 0, week: 4 }, decision_slot_ordinal: 1,
  source_evidence_id: 'src-' + player, source_evidence_fingerprint: b, provenance: 'test'
})
const evidence = (patch = {}) => ({
  saved_revision_id: 'rev-1', source_plan_fingerprint: a, event_id: 'event-x',
  entrants: [
    { player_id: 'P1', draw_role: 'direct_main', first_entry: trigger('P1', 'event-x') },
    { player_id: 'P2', draw_role: 'wild_card',
      first_entry: trigger('P2', 'event-w', 'definitive_wild_card_assignment') },
    { player_id: 'P3', draw_role: 'qualification', first_entry: null }
  ], ...patch
})
function mount(cs = false) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>
    <SavedDrawNativeReadiness runId="run-a" branchId="branch-a" revisionId="rev-1"
      eventId="event-x" season="2000/2001" cs={cs} />
  </QueryClientProvider>)
}

describe('SavedDrawNativeReadiness', () => {
  beforeEach(() => {
    api.getSavedDrawNativePreflight.mockReset()
    api.getSavedDrawEntryEvidence.mockReset()
  })

  it('shows point gaps and exactly which participants lack recorded first Entry', async () => {
    api.getSavedDrawNativePreflight.mockResolvedValue(preflight())
    api.getSavedDrawEntryEvidence.mockResolvedValue(evidence())
    mount()
    await screen.findByText(/Ranked point table is incomplete/)
    const region = screen.getByRole('region', { name: 'Saved Draw native readiness' })
    expect(api.getSavedDrawNativePreflight).toHaveBeenCalledWith(
      'run-a', 'branch-a', 'event-x', '2000/2001', 'rev-1')
    expect(api.getSavedDrawEntryEvidence).toHaveBeenCalledWith(
      'run-a', 'branch-a', 'event-x', '2000/2001', 'rev-1')
    expect(within(region).getByText(/Ranked point table is incomplete/)).toBeInTheDocument()
    expect(within(region).getByText('Missing stages: F')).toBeInTheDocument()
    expect(within(region).getByText(
      'Participants: 3 · with recorded first Entry: 2 · without: 1')).toBeInTheDocument()
    const rows = within(region).getAllByRole('row').slice(1)
    expect(within(rows[0]).getByText(/valid application · this Edition · season index 0 · week 4/))
      .toBeInTheDocument()
    expect(within(rows[1]).getByText(/definitive wild card · another Edition event-w/))
      .toBeInTheDocument()
    expect(within(rows[2]).getByText('Not established by this Saved revision')).toBeInTheDocument()
    expect(within(region).queryByRole('button')).not.toBeInTheDocument()
  })

  it('offers no readiness claim for an Unranked Draw beyond a separate preview', async () => {
    api.getSavedDrawNativePreflight.mockResolvedValue(preflight({
      ranking_status: 'unranked', point_table_status: 'not_required',
      required_point_stages: [], missing_point_stages: [],
      native_execution_status: 'requires_adoption_preview'
    }))
    api.getSavedDrawEntryEvidence.mockResolvedValue(evidence())
    mount(true)
    expect(await screen.findByText(/samostatný náhled přijetí/)).toBeInTheDocument()
    expect(screen.getByText('Není vyžadována')).toBeInTheDocument()
    expect(screen.getByText('V této uložené revizi není doloženo')).toBeInTheDocument()
  })

  it('treats an unsupported Saved Draw as information, not a crash', async () => {
    const { ApiError } = await import('../api/client')
    api.getSavedDrawNativePreflight.mockRejectedValue(new ApiError(JSON.stringify({
      detail: { code: 'saved_native_draw_conflict', message: 'Draw geometry is unsupported' }
    }), 409))
    api.getSavedDrawEntryEvidence.mockRejectedValue(new ApiError('{}', 409))
    mount()
    expect(await screen.findByText(
      /Native readiness is unavailable for this Saved Draw: Draw geometry is unsupported/))
      .toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it.each([
    ['another revision', { saved_revision_id: 'rev-2' }],
    ['another Edition', { event_id: 'event-y' }],
    ['another Draw source', { source_plan_fingerprint: b }]
  ])('does not display evidence for %s', async (_name, patch) => {
    api.getSavedDrawNativePreflight.mockResolvedValue(preflight())
    api.getSavedDrawEntryEvidence.mockResolvedValue(evidence(patch))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent(/was not displayed/)
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
})
