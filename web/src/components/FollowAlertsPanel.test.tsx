import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { FollowAlertsPanel } from './FollowAlertsPanel'

// Component contract tests: the API boundary is mocked, not the production HTTP/SQLite stack.
const api = vi.hoisted(() => ({
  getRunFollows: vi.fn(), putRunFollow: vi.fn(), deleteRunFollow: vi.fn(),
  getFollowAlerts: vi.fn(), putAlertState: vi.fn()
}))
vi.mock('../api/client', () => ({
  ...api,
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status = 500) { super(message); this.status = status }
  }
}))

const f = 'f'.repeat(64)
const e = 'e'.repeat(64)
const key = 'a'.repeat(64)
const follows = (rows: unknown[] = [{ kind: 'player', subject_id: 'P1', alerts_enabled: true }]) =>
  ({ schema_version: 'run_follows.v1', run_id: 'run', follows: rows })
const item = (kind: string, fp: string, rank?: number) => ({
  player_id: 'P1', player_name: 'Alice', country_code: 'CZE', kind,
  effective_week: { season_index: 0, week: 10 }, detail: rank ? { rank } : {},
  source: { kind: kind === 'first_recorded_title' ? 'played_edition' : 'published_ranking', fingerprint: fp },
  reasons: ['player:P1', 'country:CZE:domestic_leader']
})
const card = (state = 'unread') => ({
  notification_key: key, player_id: 'P1', player_name: 'Alice', country_code: 'CZE',
  first_week: { season_index: 0, week: 10 }, last_week: { season_index: 0, week: 11 },
  item_count: 2, unread_items: state === 'unread' ? 2 : 0, reasons: ['player:P1', 'country:CZE:domestic_leader'],
  items: [item('first_recorded_title', e), item('first_top_rank', f, 3)], state
})
const alerts = (cards: unknown[] = [card()]) => ({
  schema_version: 'native_tour_notifications.v1', run_id: 'run', branch_id: 'branch',
  saved_head_revision_id: 'rev-1', as_of_ordinal: 12, unread_cards: cards.length, cards,
  criteria: { domestic_leaders: 3, exceptional_rank: 1, group_window_weeks: 2, status: 'provisional calibration' }
})
function mount(cs = false) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(<MemoryRouter><QueryClientProvider client={client}>
    <FollowAlertsPanel runId="run" branchId="branch" savedHead="rev-1" cs={cs} /></QueryClientProvider></MemoryRouter>)
}

describe('FollowAlertsPanel (component, mocked API)', () => {
  beforeEach(() => { Object.values(api).forEach(m => m.mockReset()); api.getRunFollows.mockResolvedValue(follows()); api.getFollowAlerts.mockResolvedValue(alerts()) })

  it('shows ONE grouped card with separately sourced details and the dedup reasons', async () => {
    mount()
    const cardRow = await screen.findByLabelText(/^Alice /)
    expect(cardRow).toHaveTextContent('2 milestones')
    expect(cardRow).toHaveTextContent('followed player; followed country: domestic leader')
    expect(screen.getAllByLabelText(/^Alice /)).toHaveLength(1)
    const details = within(cardRow).getByText('Details and sources').closest('details')!
    expect(details).toHaveTextContent('First recorded title')
    expect(details).toHaveTextContent('played_edition · eeeeeeeeeeee')
    expect(details).toHaveTextContent('First recorded TOP 100 · season 1 · week 10 · #3')
    expect(screen.getByText(/provisional calibration/)).toBeInTheDocument()
  })

  it('marks read and hides through the state endpoint without removing anything locally', async () => {
    api.putAlertState.mockResolvedValue(alerts())
    mount()
    await screen.findByLabelText(/^Alice /)
    fireEvent.click(screen.getByRole('button', { name: 'Mark as read' }))
    await waitFor(() => expect(api.putAlertState).toHaveBeenCalledWith('run', 'branch', key, 'read', 2))
    fireEvent.click(screen.getByRole('button', { name: 'Hide' }))
    await waitFor(() => expect(api.putAlertState).toHaveBeenLastCalledWith('run', 'branch', key, 'hidden', 2))
  })

  it('follows an upper-cased country, mutes and unfollows through the Run endpoints (CS)', async () => {
    api.putRunFollow.mockResolvedValue(follows())
    api.deleteRunFollow.mockResolvedValue(follows([]))
    mount(true)
    await screen.findByText('Sledované')
    fireEvent.change(screen.getByLabelText('Typ'), { target: { value: 'country' } })
    fireEvent.change(screen.getByLabelText('ID hráče / kód země'), { target: { value: 'cze' } })
    fireEvent.click(screen.getByRole('button', { name: 'Sledovat' }))
    await waitFor(() => expect(api.putRunFollow).toHaveBeenCalledWith('run', 'country', 'CZE', true))
    fireEvent.click(screen.getByRole('button', { name: 'Ztišit' }))
    await waitFor(() => expect(api.putRunFollow).toHaveBeenLastCalledWith('run', 'player', 'P1', false))
    fireEvent.click(screen.getByRole('button', { name: 'Přestat sledovat' }))
    await waitFor(() => expect(api.deleteRunFollow).toHaveBeenCalledWith('run', 'player', 'P1'))
  })

  it('does not display alerts for another Saved revision or Branch', async () => {
    api.getFollowAlerts.mockResolvedValue({ ...alerts(), saved_head_revision_id: 'rev-2' })
    mount()
    expect(await screen.findByText(/was not displayed/)).toBeInTheDocument()
    expect(screen.queryByLabelText(/^Alice /)).not.toBeInTheDocument()
  })

  it('treats an unsupported Run as information and an empty list as history-preserving', async () => {
    api.getFollowAlerts.mockImplementation(async () => { throw new Error('Notifications require a Saved configured Tour') })
    mount()
    expect(await screen.findByText(/Alerts are unavailable for this revision/)).toHaveTextContent('Saved configured Tour')
  })

  it('reads alerts again after a follow even if the first read is still slow (no stale empty list)', async () => {
    let release: (v: unknown) => void = () => undefined
    api.getRunFollows.mockResolvedValueOnce(follows([])).mockResolvedValue(follows())
    api.putRunFollow.mockResolvedValue(follows())
    api.getFollowAlerts.mockImplementationOnce(() => new Promise(resolve => { release = resolve }))
      .mockResolvedValue(alerts())
    mount()
    await screen.findByText('You follow nothing yet.')
    fireEvent.change(screen.getByLabelText('Player ID / country code'), { target: { value: 'P1' } })
    fireEvent.click(screen.getByRole('button', { name: 'Follow' }))
    // The new follow set triggers its own read; the slow first one is irrelevant.
    expect(await screen.findByLabelText(/^Alice /)).toBeInTheDocument()
    release(alerts([]))
    await waitFor(() => expect(api.getFollowAlerts.mock.calls.length).toBeGreaterThanOrEqual(2))
    expect(screen.getByLabelText(/^Alice /)).toBeInTheDocument()
  })

  it('says that facts stay in history when there is no alert', async () => {
    api.getFollowAlerts.mockResolvedValue(alerts([]))
    mount()
    expect(await screen.findByText(/facts stay in the players’ career history/)).toBeInTheDocument()
  })
})
