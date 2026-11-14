import { MemoryRouter } from 'react-router-dom'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SavedPlayerCareerTimeline } from './SavedPlayerCareerTimeline'

// Component contract tests: the API boundary is mocked, not the production HTTP/SQLite stack.
const api = vi.hoisted(() => ({ getSavedPlayerCareer: vi.fn() }))
vi.mock('../api/client', () => ({
  ...api,
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status = 500) { super(message); this.status = status }
  }
}))

const f = 'f'.repeat(64)
const e = 'e'.repeat(64)
const turnPro = { kind: 'turn_pro', effective_week: { season_index: 0, week: 4 }, detail: {},
  source: { kind: 'player_ai_decision', fingerprint: f } }
const title = { kind: 'edition_result', effective_week: { season_index: 0, week: 10 },
  detail: { name: 'Open', reached_stage: 'champion', awarded_points: 100 },
  source: { kind: 'played_edition', fingerprint: e } }
const first = { ...title, kind: 'first_recorded_title' }
const data = (asOf: number, timeline: unknown[], milestones: unknown[]) => ({
  schema_version: 'native_player_career.v1', run_id: 'run', branch_id: 'branch',
  saved_head_revision_id: 'rev-1', source_tour_fingerprint: f, as_of_ordinal: asOf,
  player: { player_id: 'P1', name: 'P', country_code: 'CZE' },
  covered_period: { first_recorded_ranking_ordinal: 1, note: 'Coverage starts with the first ranking.' },
  overview: { status: 'professional', titles: timeline.includes(title) ? 1 : 0, finals: 0,
    editions_played: timeline.includes(title) ? 1 : 0, career_high_rank: null, current_rank: null },
  milestones, timeline, unsupported: ['injury'],
})
function mount(cs = false) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<MemoryRouter><QueryClientProvider client={client}>
    <SavedPlayerCareerTimeline runId="run" branchId="branch" savedHead="rev-1" playerId="P1" cs={cs} />
  </QueryClientProvider></MemoryRouter>)
}

describe('SavedPlayerCareerTimeline (component, mocked API)', () => {
  beforeEach(() => { api.getSavedPlayerCareer.mockClear() })

  it('shows milestones with sources, the recorded-not-lifetime note and unsupported injuries', async () => {
    api.getSavedPlayerCareer.mockResolvedValue(data(12, [turnPro, title], [turnPro, first]))
    mount()
    await screen.findByText(/Open · champion · 100 pts/)
    const region = screen.getByRole('region', { name: 'Career: timeline and milestones' })
    expect(within(region).getAllByText(/First recorded title/).length).toBeGreaterThan(0)
    expect(region).toHaveTextContent(/does not mean first ever/)
    expect(region).toHaveTextContent(/Injuries and returns have no supported source/)
    expect(region).toHaveTextContent(/played_edition · eeeeeeeeeeee/)
    expect(region).toHaveTextContent(/Open · champion · 100 pts/)
  })

  it('requests an earlier week and then shows no future title', async () => {
    api.getSavedPlayerCareer.mockImplementation(async (_r, _b, _p, asOf) =>
      asOf === 5 ? data(5, [turnPro], [turnPro]) : data(12, [turnPro, title], [turnPro, first]))
    mount()
    await screen.findByText(/champion · 100 pts/)
    fireEvent.change(screen.getByLabelText(/View as of week/), { target: { value: '5' } })
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }))
    await screen.findByText(/Shown as of week no\. 5/)
    expect(api.getSavedPlayerCareer).toHaveBeenLastCalledWith('run', 'branch', 'P1', 5)
    expect(screen.queryByText(/champion · 100 pts/)).not.toBeInTheDocument()
    expect(screen.queryByRole('listitem', { name: /First recorded title/ })).not.toBeInTheDocument()
    expect(screen.queryAllByText(/First recorded title/).filter(n => n.tagName !== 'OPTION')).toHaveLength(0)
  })

  it('filters the timeline by type and renders Czech', async () => {
    api.getSavedPlayerCareer.mockResolvedValue(data(12, [turnPro, title], [turnPro, first]))
    mount(true)
    await screen.findByText(/Open · vítěz · 100 b\./)
    const region = screen.getByRole('region', { name: 'Kariéra: časová osa a milníky' })
    expect(region).toHaveTextContent(/První zaznamenaný titul/)
    expect(region).toHaveTextContent(/Zranění a návraty zatím nemají podporovaný zdroj/)
    fireEvent.change(screen.getByLabelText('Typ'), { target: { value: 'turn_pro' } })
    const list = within(screen.getAllByRole('list').slice(-1)[0])
    expect(list.queryByText(/Výsledek Edice/)).not.toBeInTheDocument()
    expect(list.getByText(/Přechod mezi profesionály/)).toBeInTheDocument()
  })

  it('does not display a response for another Saved revision or player', async () => {
    api.getSavedPlayerCareer.mockResolvedValue({ ...data(12, [turnPro], [turnPro]), saved_head_revision_id: 'rev-2' })
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent(/was not displayed/)
    expect(screen.queryByText(/Turned professional/)).not.toBeInTheDocument()
  })

  it('shows the retirement summary and the never-pro exception without implying a cause', async () => {
    const retire = { kind: 'retirement', effective_week: { season_index: 0, week: 6 }, detail: { without_turn_pro: true },
      source: { kind: 'week_transition', fingerprint: 'c'.repeat(64) } }
    const summary = { retired_week: { season_index: 0, week: 6 }, turn_pro_rule: true, without_turn_pro: true,
      without_tour_entry: null, opening_professional: false, entry_week: null, titles: 0, finals: 0,
      editions_played: 0, first_recorded_title_week: null, career_high_rank: 12,
      source: retire.source, note: 'n' }
    api.getSavedPlayerCareer.mockResolvedValue({
      ...data(12, [retire], [retire]), overview: { status: 'retired', titles: 0, finals: 0, editions_played: 0, career_high_rank: 12, current_rank: null },
      retirement_summary: summary })
    mount()
    const block = await screen.findByLabelText('Career summary')
    expect(block).toHaveTextContent('Master v87 exception')
    expect(block).toHaveTextContent('No Turn Pro event or health cause is implied')
    expect(block).toHaveTextContent('week_transition · cccccccccccc')
    expect(screen.getAllByText(/exception: without ever turning pro/).length).toBeGreaterThan(0)
  })

  it('does not display a retired player whose summary is missing or unbacked', async () => {
    api.getSavedPlayerCareer.mockResolvedValue({
      ...data(12, [turnPro], [turnPro]), overview: { status: 'retired', titles: 0, finals: 0, editions_played: 0, career_high_rank: null, current_rank: null } })
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent(/was not displayed/)
  })

  it('treats an unsupported Run as information', async () => {
    api.getSavedPlayerCareer.mockImplementation(async () => {
      throw new Error('Player career requires a Saved configured Tour')
    })
    mount()
    const status = await screen.findByText(/unavailable for this revision/)
    expect(status).toHaveTextContent('Player career requires a Saved configured Tour')
  })
  it('accepts ordinal zero without converting it to present, and rejects future ordinals', async () => {
    api.getSavedPlayerCareer.mockImplementation(async (_r, _b, _p, asOf) =>
      asOf === 0 ? data(0, [], []) : data(12, [turnPro, title], [turnPro, first]))
    mount()
    await screen.findByText(/champion · 100 pts/)
    fireEvent.change(screen.getByLabelText(/View as of week/), { target: { value: '0' } })
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }))
    await screen.findByText(/Shown as of week no\. 0/)
    expect(api.getSavedPlayerCareer).toHaveBeenCalledWith('run', 'branch', 'P1', 0)
    fireEvent.change(screen.getByLabelText(/View as of week/), { target: { value: '99' } })
    fireEvent.click(screen.getByRole('button', { name: 'Apply' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/Invalid or future week/)
    expect(api.getSavedPlayerCareer).not.toHaveBeenCalledWith('run', 'branch', 'P1', 99)
  })

})
