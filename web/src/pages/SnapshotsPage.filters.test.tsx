import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SnapshotsPage } from './SnapshotsPage'

const api = vi.hoisted(() => ({
  getRun: vi.fn(),
  listEvents: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn(),
  ApiError: class ApiError extends Error { status = 500 }
}))
vi.mock('../api/client', () => api)
vi.mock('../i18n/LanguageContext', () => ({ useLanguage: () => ({ language: 'en' }) }))

function Controls(): JSX.Element {
  const navigate = useNavigate()
  const location = useLocation()
  return <>
    <output aria-label="Current query">{location.search}</output>
    <button onClick={() => navigate(-1)}>Back</button>
    <button onClick={() => navigate(1)}>Forward</button>
  </>
}

function renderPage(mode: 'ranking' | 'race', query = '', runId = 'run-a'): ReturnType<typeof render> {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter initialEntries={[`/runs/${runId}/snapshots/${mode}${query}`]}>
      <Controls />
      <Routes><Route path="/runs/:runId/snapshots/:kind" element={<SnapshotsPage mode={mode} />} /></Routes>
    </MemoryRouter>
  </QueryClientProvider>)
}

describe('SnapshotsPage URL-backed Ranking/Race history filters', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2027 },
      season_state: {
        season: 2027,
        ordered_events: [
          { event_id: 'E1', season: 2027, week: 8, category: 'Gold', tour: 'Tour', template_id: 'FIRST' },
          { event_id: 'E2', season: 2027, week: 9, category: 'Diamond', tour: 'Tour', template_id: 'SECOND' }
        ]
      }
    })
    api.listEvents.mockResolvedValue({ run_id: 'run-a', events: [
      { event_sequence: 1, event_id: 'E1', season: 2027, week: 8, template_id: 'FIRST', tournament_result: null },
      { event_sequence: 2, event_id: 'E2', season: 2027, week: 9, template_id: 'SECOND', tournament_result: null }
    ] })
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [
      { snapshot_sequence: 4, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: { name: 'ranking-4' } },
      { snapshot_sequence: 3, snapshot_kind: 'WEEK', source_event_id: 'E1', payload: { name: 'ranking-3' } }
    ] })
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [
      { snapshot_sequence: 2, snapshot_kind: 'WEEK', source_event_id: 'E1', payload: { name: 'race-2' } },
      { snapshot_sequence: 3, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: { name: 'race-3' } }
    ] })
  })

  it('restores an exact Ranking snapshot plus all three URL filters on a fresh mount', async () => {
    const query = '?foreign=keep&filterWeek=8&filterCategory=Gold&filterSourceEvent=E1&selectedSequence=3&selectedMode=ranking&selectedRun=run-a'
    const first = renderPage('ranking', query)
    let list = await screen.findByRole('list', { name: 'Ranking snapshots list' })
    expect(within(list).getAllByRole('button')).toHaveLength(1)
    expect(within(list).getByRole('button', { name: /3\. WEEK/ })).toHaveAttribute('aria-current', 'true')
    expect(screen.getByLabelText('Filter snapshots by week')).toHaveValue('8')
    expect(screen.getByLabelText('Filter snapshots by category')).toHaveValue('Gold')
    expect(screen.getByLabelText('Filter snapshots by source event')).toHaveValue('E1')
    expect(screen.getByRole('link', { name: 'Open dedicated snapshot detail page' })).toHaveAttribute('href', '/runs/run-a/snapshots/ranking/3')
    first.unmount()

    renderPage('ranking', query)
    list = await screen.findByRole('list', { name: 'Ranking snapshots list' })
    expect(within(list).getByRole('button', { name: /3\. WEEK/ })).toHaveAttribute('aria-current', 'true')
    expect(await screen.findByText(/ranking-3/)).toBeInTheDocument()
  })

  it('supports Race filter history, exact selection and reset without erasing foreign parameters', async () => {
    const user = userEvent.setup()
    renderPage('race', '?foreign=keep')
    const list = await screen.findByRole('list', { name: 'Race snapshots list' })
    await user.selectOptions(screen.getByLabelText('Filter snapshots by week'), '9')
    expect(within(list).getByRole('button', { name: /3\. WEEK/ })).toHaveAttribute('aria-current', 'true')
    expect(screen.getByLabelText('Current query')).toHaveTextContent('filterWeek=9')
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByLabelText('Filter snapshots by week')).toHaveValue('')
    await user.click(screen.getByRole('button', { name: 'Forward' }))
    expect(screen.getByLabelText('Filter snapshots by week')).toHaveValue('9')
    await user.click(within(list).getByRole('button', { name: /3\. WEEK/ }))
    expect(screen.getByLabelText('Current query')).toHaveTextContent('selectedSequence=3')
    expect(screen.getByLabelText('Current query')).toHaveTextContent('selectedMode=race')
    expect(screen.getByLabelText('Current query')).toHaveTextContent('selectedRun=run-a')
    await user.click(screen.getByRole('button', { name: 'Reset filters' }))
    expect(screen.getByLabelText('Current query')).toHaveTextContent('foreign=keep')
    expect(screen.getByLabelText('Current query')).not.toHaveTextContent('filterWeek')
    expect(within(list).getAllByRole('button')).toHaveLength(2)
    expect(within(list).getByRole('button', { name: /3\. WEEK/ })).toHaveAttribute('aria-current', 'true')
  })

  it('ignores a scoped selectedSequence copied into another mode or Run', async () => {
    const query = '?selectedSequence=3&selectedMode=ranking&selectedRun=run-a'
    const race = renderPage('race', query)
    const raceList = await screen.findByRole('list', { name: 'Race snapshots list' })
    expect(within(raceList).getByRole('button', { name: /2\. WEEK/ })).toHaveAttribute('aria-current', 'true')
    expect(await screen.findByText(/race-2/)).toBeInTheDocument()
    expect(screen.queryByText(/race-3/)).not.toBeInTheDocument()
    race.unmount()

    const foreign = renderPage('ranking', '?selectedSequence=3&selectedMode=ranking&selectedRun=another-run')
    const rankingList = await screen.findByRole('list', { name: 'Ranking snapshots list' })
    expect(within(rankingList).getByRole('button', { name: /4\. WEEK/ })).toHaveAttribute('aria-current', 'true')
    expect(await screen.findByText(/ranking-4/)).toBeInTheDocument()
    foreign.unmount()
  })

  it('rejects malformed sequence and invalid numeric filter values without interpreting null as a source week', async () => {
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [
      { snapshot_sequence: 3, snapshot_kind: 'WEEK', source_event_id: 'NO-WEEK', payload: { name: 'unknown-week-snapshot' } }
    ] })
    api.listEvents.mockResolvedValue({ run_id: 'run-a', events: [
      { event_sequence: 7, event_id: 'NO-WEEK', week: null, season: 2026, template_id: null, tournament_result: null }
    ] })
    renderPage('ranking', '?filterWeek=null&selectedSequence=3abc')
    expect(await screen.findByText('No snapshots match the current filters.')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Unknown week: null' })).toBeInTheDocument()
    expect(screen.queryByText(/unknown-week-snapshot/)).not.toBeInTheDocument()
  })

  it('keeps source event ID search as free text and removes an obsolete selection after changing filters', async () => {
    const user = userEvent.setup()
    renderPage('ranking', '?selectedSequence=4&selectedMode=ranking&selectedRun=run-a&foreign=keep')
    await screen.findByRole('list', { name: 'Ranking snapshots list' })
    await user.selectOptions(screen.getByLabelText('Filter snapshots by week'), '8')
    expect(screen.getByLabelText('Current query')).not.toHaveTextContent('selectedSequence')
    expect(screen.getByRole('button', { name: /3\. WEEK/ })).toHaveAttribute('aria-current', 'true')
    await user.type(screen.getByLabelText('Filter snapshots by source event'), 'E1')
    expect(screen.getByLabelText('Current query')).toHaveTextContent('filterSourceEvent=E1')
    expect(screen.getByLabelText('Current query')).toHaveTextContent('foreign=keep')
  })

  it('hides foreign Run snapshot records and keeps the existing source identity guard', async () => {
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'other-run', snapshots: [
      { snapshot_sequence: 3, snapshot_kind: 'WEEK', source_event_id: 'E1', payload: { secret: 'other-world' } }
    ] })
    renderPage('ranking', '?filterSourceEvent=E1')
    expect(await screen.findByText('Snapshot history belongs to another Run; its records are hidden.')).toBeInTheDocument()
    expect(screen.queryByText(/other-world/)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open dedicated snapshot detail page' })).not.toBeInTheDocument()
  })
  it('retains the Ranking exact bookmark when typing a source filter during list loading', async () => {
    const user = userEvent.setup()
    let resolveSnapshots!: (value: unknown) => void
    api.listRankingSnapshots.mockReturnValue(new Promise(resolve => { resolveSnapshots = resolve }))
    renderPage('ranking', '?selectedSequence=3&selectedMode=ranking&selectedRun=run-a')
    await user.type(screen.getByLabelText('Filter snapshots by source event'), 'E1')
    expect(screen.getByLabelText('Current query')).toHaveTextContent('selectedSequence=3')
    expect(screen.getByLabelText('Current query')).toHaveTextContent('selectedMode=ranking')
    expect(screen.getByLabelText('Current query')).toHaveTextContent('filterSourceEvent=E1')
    await act(async () => { resolveSnapshots({ run_id: 'run-a', snapshots: [
      { snapshot_sequence: 4, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: {} },
      { snapshot_sequence: 3, snapshot_kind: 'WEEK', source_event_id: 'E1', payload: { name: 'stored-three' } }
    ] }) })
    const list = await screen.findByRole('list', { name: 'Ranking snapshots list' })
    expect(within(list).getByRole('button', { name: /3\\. WEEK/ })).toHaveAttribute('aria-current', 'true')
    expect(await screen.findByText(/stored-three/)).toBeInTheDocument()
  })

  it('keeps an unavailable source week distinguishable from an unknown week', async () => {
    api.listEvents.mockRejectedValue(new Error('source events offline'))
    api.getRun.mockRejectedValue(new Error('plan offline'))
    renderPage('ranking', '?filterWeek=9')
    expect(await screen.findByText('No snapshots match the current filters.')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Week not verified: 9' })).toBeInTheDocument()
    expect(screen.getByText(/cannot yet be verified from loaded sources/)).toBeInTheDocument()
  })

  it.each(['3abc', 'null', 'undefined', '3.5', '-3'])(
    'never accepts a malformed selectedSequence=%s as a matching numeric snapshot', async (malformed) => {
      renderPage('ranking', `?selectedSequence=${encodeURIComponent(malformed)}`)
      const list = await screen.findByRole('list', { name: 'Ranking snapshots list' })
      expect(within(list).getByRole('button', { name: /4\\. WEEK/ })).toHaveAttribute('aria-current', 'true')
      expect(within(list).getByRole('button', { name: /3\\. WEEK/ })).not.toHaveAttribute('aria-current')
      expect(await screen.findByText(/ranking-4/)).toBeInTheDocument()
    }
  )

})
