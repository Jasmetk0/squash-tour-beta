import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../i18n/LanguageContext'
import { ActivityPage } from './ActivityPage'
import { EventsPage } from './EventsPage'
import { SnapshotsPage } from './SnapshotsPage'
import { FinalsResultDetailPage } from './FinalsResultDetailPage'

const api = vi.hoisted(() => ({
  getRunActivity: vi.fn(), getRun: vi.fn(), listEvents: vi.fn(), getEvent: vi.fn(),
  listRankingSnapshots: vi.fn(), listRaceSnapshots: vi.fn(),
  getFinalsSummary: vi.fn(), getFinalsResult: vi.fn()
}))
vi.mock('../api/client', () => api)

const event = (eventId: string, eventSequence: number, result: Record<string, unknown> | null = null) => ({
  event_id: eventId, event_sequence: eventSequence, week: eventSequence, season: 2027,
  template_id: 'TEMPLATE', tournament_result: result
})
const item = (eventId: string, index: number) => ({
  kind: 'event', label: eventId, sequence: index, season: 2027, week: index,
  event_id: eventId, source_event_id: null, snapshot_sequence: null, related_run_id: null
})

function LanguageToggle(): JSX.Element {
  const { language, setLanguage } = useLanguage()
  return <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Switch locale</button>
}

function renderHistory(ui: JSX.Element, route: string): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <LanguageProvider>
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[route]}>
          <LanguageToggle />
          <Routes><Route path="/runs/:runId/*" element={ui} /></Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </LanguageProvider>
  )
}

describe('Run historical UI CS/EN read-only behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('squash-engine-language-v1', 'en')
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2027 },
      season_state: { ordered_events: [
        { event_id: 'E1', week: 1, tour: 'W', category: 'GOLD', template_id: 'TEMPLATE' },
        { event_id: 'E2', week: 2, tour: 'W', category: 'GOLD', template_id: 'TEMPLATE' }
      ] }
    })
    api.listEvents.mockResolvedValue({ run_id: 'run-a', events: [event('E1', 1), event('E2', 2, { score: 0 })] })
    api.getEvent.mockImplementation((_runId: string, id: string) =>
      Promise.resolve(id === 'E1' ? event('E1', 1) : event('E2', 2, { score: 0 })))
    api.getRunActivity.mockResolvedValue({ run_id: 'run-a', items: [item('E1', 1), item('E2', 2)] })
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [
      { snapshot_sequence: 1, snapshot_kind: 'WEEK', source_event_id: 'E1', payload: { points: 0 } }
    ] })
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [] })
  })

  it('preserves an active activity filter and selection across language changes without another request', async () => {
    const user = userEvent.setup()
    renderHistory(<ActivityPage />, '/runs/run-a/activity')
    const list = await screen.findByRole('list', { name: 'Run activity feed list' })
    expect(within(list).getAllByRole('button')).toHaveLength(2)
    await user.type(screen.getByLabelText('Filter activity by label or identifier text'), 'E2')
    expect(within(list).getAllByRole('button')).toHaveLength(1)

    await user.click(screen.getByRole('button', { name: 'Switch locale' }))
    expect(screen.getByText('Aktivita Runu')).toBeInTheDocument()
    expect(screen.getByLabelText('Filtrovat podle popisu nebo identifikátoru')).toHaveValue('E2')
    expect(within(screen.getByRole('list', { name: 'Seznam aktivity Runu' })).getAllByRole('button')).toHaveLength(1)
    expect(api.getRunActivity).toHaveBeenCalledTimes(1)
    expect(api.getEvent).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(within(screen.getByRole('list', { name: 'Seznam aktivity Runu' })).getAllByRole('button')).toHaveLength(2)
  })

  it('keeps a selected event and distinguishes an absent result from a stored zero-valued result', async () => {
    const user = userEvent.setup()
    renderHistory(<EventsPage />, '/runs/run-a/events')
    const list = await screen.findByRole('list', { name: 'Events history list' })
    expect(await screen.findByText('No tournament result evidenced')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Switch locale' }))
    expect(screen.getByText('Turnajový výsledek není doložen')).toBeInTheDocument()
    const buttons = within(screen.getByRole('list', { name: 'Seznam historických událostí' })).getAllByRole('button')
    await user.click(buttons[1])
    expect(await screen.findByText('Turnajový výsledek uložen')).toBeInTheDocument()
    expect(within(list).getAllByRole('button')).toHaveLength(2)
    expect(api.listEvents).toHaveBeenCalledTimes(1)
  })

  it('marks saved snapshot history as historical and never invents a timestamp', async () => {
    const user = userEvent.setup()
    renderHistory(<SnapshotsPage mode="ranking" />, '/runs/run-a/snapshots/ranking')
    expect(await screen.findByText('Stored historical snapshot; it is not necessarily the current ranking. The endpoint does not provide a timestamp.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Switch locale' }))
    expect(screen.getByText('Uložený historický snímek, nikoli nutně aktuální žebříček. Endpoint neposkytuje časové razítko.')).toBeInTheDocument()
    expect(api.listRankingSnapshots).toHaveBeenCalledTimes(1)
    expect(api.listRaceSnapshots).toHaveBeenCalledTimes(1)
  })

  it('rejects explicitly foreign activity lists without presenting them as empty history', async () => {
    api.getRunActivity.mockResolvedValue({ run_id: 'foreign-run', items: [item('E1', 1)] })
    renderHistory(<ActivityPage />, '/runs/run-a/activity')
    expect(await screen.findByRole('alert')).toHaveTextContent('Activity response belongs to another Run; its records are hidden.')
    expect(screen.queryByText('No activity has been persisted for this run yet.')).not.toBeInTheDocument()
  })
  it('changes language while a read is pending without replacing its request or data', async () => {
    let resolveActivity!: (payload: unknown) => void
    api.getRunActivity.mockReturnValue(new Promise((resolve) => { resolveActivity = resolve }))
    const user = userEvent.setup()
    renderHistory(<ActivityPage />, '/runs/run-a/activity')
    expect(screen.getByText('Loading activity feed...')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Switch locale' }))
    expect(screen.getByText('Načítání aktivity…')).toBeInTheDocument()
    resolveActivity({ run_id: 'run-a', items: [item('E1', 1)] })
    expect(await screen.findByRole('list', { name: 'Seznam aktivity Runu' })).toBeInTheDocument()
    expect(api.getRunActivity).toHaveBeenCalledTimes(1)
    expect(api.getRunActivity).toHaveBeenCalledWith('run-a')
  })

  it('refetches only the read-only activity resource when Refresh is clicked', async () => {
    const user = userEvent.setup()
    renderHistory(<ActivityPage />, '/runs/run-a/activity')
    await screen.findByRole('list', { name: 'Run activity feed list' })
    await user.click(screen.getByRole('button', { name: 'Refresh read-only data' }))
    await waitFor(() => expect(api.getRunActivity).toHaveBeenCalledTimes(2))
    expect(api.getRun).toHaveBeenCalledTimes(1)
    expect(api.listEvents).toHaveBeenCalledTimes(1)
  })

  it('never fabricates a Finals result from available qualification and keeps 404 separate from read failure', async () => {
    api.getFinalsSummary.mockResolvedValue({
      run_id: 'run-a', season: 2027,
      qualification: { run_id: 'run-a', season: 2027 }, result: null
    })
    api.getFinalsResult.mockRejectedValue({ status: 404, message: 'No stored result' })
    const user = userEvent.setup()
    renderHistory(<FinalsResultDetailPage />, '/runs/run-a/finals/result')
    expect(await screen.findByText('Finals result has not been recorded for this run yet.')).toBeInTheDocument()
    expect(screen.queryByText('P1')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Switch locale' }))
    expect(screen.getByText('Pro tento Run nebyl v tomto zdroji nalezen uložený výsledek Finals.')).toBeInTheDocument()
    expect(api.getFinalsResult).toHaveBeenCalledTimes(1)
  })

})
