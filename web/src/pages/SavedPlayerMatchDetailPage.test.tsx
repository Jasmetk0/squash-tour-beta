import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SavedPlayerMatchDetailPage } from './SavedPlayerMatchDetailPage'
import { LanguageProvider, useLanguage } from '../i18n/LanguageContext'

const api = vi.hoisted(() => ({
  getSavedPlayerMatchDetail: vi.fn(), getSavedHomePlayerIdentities: vi.fn(),
}))
vi.mock('../api/client',()=>({...api,ApiError:class ApiError extends Error{}}))
const branchContext = vi.hoisted(() => ({
  current: { run_id: 'run', branch_id: 'branch', saved_head_revision_id: 'rev' }
}))
vi.mock('../admin/AdminBranchContext', () => ({
  useAdminBranch: () => ({ selectedBranch: branchContext.current, isLoading: false, error: null }),
}))
vi.mock('../admin/AdminTimeContext', () => ({ useAdminTime: () => ({ mode: 'present' }) }))

function LanguageSwitch() { const { setLanguage } = useLanguage(); return <button onClick={() => setLanguage('en')}>Test English</button> }

function mount(entry = '/admin/runs/run/people/A/matches/event/final') {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  const tree = () => <QueryClientProvider client={cache}><LanguageProvider><MemoryRouter
    initialEntries={[entry]}>
    <LanguageSwitch /><nav aria-label="Replay scope test navigation">
      <Link to="/admin/runs/run/people/A/matches/event/short">Switch match</Link>
      <Link to="/admin/runs/run/people/A/matches/second/final">Switch event</Link>
      <Link to="/admin/runs/run/people/B/matches/event/final">Switch player</Link>
      <Link to="/admin/runs/other-run/people/A/matches/event/final">Switch Run</Link>
    </nav>
    <Routes><Route path="/admin/runs/:runId/people/:playerId/matches/:eventId/:matchId"
      element={<SavedPlayerMatchDetailPage />} /></Routes>
  </MemoryRouter></LanguageProvider></QueryClientProvider>
  const rendered = render(tree())
  return { ...rendered, refreshBranch: () => rendered.rerender(tree()) }
}

function result(overrides: Record<string, unknown> = {}) {
  return {
    schema_version: 'saved_player_match_detail.v1', run_id: 'run',
    branch_id: 'branch', saved_revision_id: 'rev', player_id: 'A',
    source: 'selected_branch_saved_revision',
    match: { event_id: 'event', match_id: 'final', event_name: 'Championship',
      season: '2002/03', week: 17, draw_type: 'main', round_number: 2,
      completion: 'played', scoreline: '3-2', opponent_player_id: 'B', outcome: 'win' },
    winner_player_id: 'A', loser_player_id: 'B',
    player_a_id: 'A', player_b_id: 'B', replay_status: 'available',
    offset: 0, limit: 25, total_rallies: 2, has_more: false,
    rallies: [1, 2].map(i => ({
      rally_index: i, set_number: 1, server_player_id: 'A',
      winner_player_id: 'A', score_a_before: i - 1,
      score_b_before: 0, score_a_after: i, score_b_after: 0,
      sets_a_after: 0, sets_b_after: 0, set_complete: false, match_complete: false,
    })), ...overrides,
  }
}

describe('canonical saved match detail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    branchContext.current = { run_id: 'run', branch_id: 'branch', saved_head_revision_id: 'rev' }
    api.getSavedPlayerMatchDetail.mockResolvedValue(result())
    api.getSavedHomePlayerIdentities.mockImplementation(async (_r: string, _b: string, ids: string[]) => ({
      run_id: 'run', branch_id: 'branch', saved_revision_id: 'rev', source: 'selected_branch_saved_revision',
      requested_ids: ids, players: ids.map(id => ({ player_id: id, display_name: id === 'A' ? 'Alpha' : 'Bravo' })),
    }))
  })
  it('returns to the original career tab, season and page', async () => {
    mount('/admin/runs/run/people/A/matches/event/final?tab=career&careerSeason=2&careerPage=1')
    expect(await screen.findByText('Championship')).toBeInTheDocument()
    expect(screen.getByRole('link', {name: /Zpět na profil hráče/})).toHaveAttribute('href',
      '/admin/runs/run/people/A?tab=career&careerSeason=2&careerPage=1')
  })
  it('steps through archived score frames without simulating', async () => {
    mount()
    expect(await screen.findByText('Championship')).toBeInTheDocument()
    expect(screen.getByRole('link', {name: /Zpět na profil hráče/})).toHaveAttribute('href',
      '/admin/runs/run/people/A')
    expect(await screen.findByText('Alpha')).toBeInTheDocument()
    expect(screen.getByText(/1\/2/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Další výměna →' }))
    await waitFor(() => expect(screen.getByText(/2\/2/)).toBeInTheDocument())
    expect(api.getSavedPlayerMatchDetail).toHaveBeenCalledTimes(1)
  })
  it('does not invent a replay when archive missing', async () => {
    api.getSavedPlayerMatchDetail.mockResolvedValueOnce(result({
      replay_status: 'unavailable', player_a_id: null, player_b_id: null,
      total_rallies: 0, rallies: [],
    }))
    mount()
    expect(await screen.findByText(/Ověřený archiv výměn není/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Další výměna →' })).not.toBeInTheDocument()
  })
  it('hides a stale saved HEAD rather than exposing a foreign match', async () => {
    api.getSavedPlayerMatchDetail.mockResolvedValueOnce(result({ saved_revision_id: 'foreign' }))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Detail neodpovídá vybrané uložené revizi')
    expect(screen.queryByText('Championship')).not.toBeInTheDocument()
  })
})


function useLongMatchFixture(): void {
  api.getSavedPlayerMatchDetail.mockImplementation(async (
    runId: string, branchId: string, playerId: string,
    eventId: string, matchId: string, offset: number, limit: number
  ) => {
    const total = runId !== 'run' || branchId !== 'branch' ||
      branchContext.current.saved_head_revision_id !== 'rev' ||
      matchId === 'short' || eventId === 'second' || playerId === 'B' ? 2 : 30
    const original = result()
    return result({
      run_id: runId, branch_id: branchId,
      saved_revision_id: branchContext.current.saved_head_revision_id,
      player_id: playerId, offset, limit, total_rallies: total,
      has_more: offset + limit < total,
      match: { ...original.match, event_id: eventId, match_id: matchId },
      rallies: Array.from({ length: Math.max(0, Math.min(limit, total - offset)) }, (_, i) => {
        const index = offset + i + 1
        return {
          rally_index: index, set_number: 1, server_player_id: playerId,
          winner_player_id: playerId, score_a_before: index - 1,
          score_b_before: 0, score_a_after: index, score_b_after: 0,
          sets_a_after: 0, sets_b_after: 0, set_complete: false, match_complete: false
        }
      })
    })
  })
  api.getSavedHomePlayerIdentities.mockImplementation(async (
    runId: string, branchId: string, ids: string[]
  ) => ({
    run_id: runId, branch_id: branchId,
    saved_revision_id: branchContext.current.saved_head_revision_id,
    source: 'selected_branch_saved_revision', requested_ids: ids, players: ids.map(id => ({ player_id: id, display_name: id }))
  }))
}
async function seekSecondPage(): Promise<void> {
  expect(await screen.findByText(/1\/30/)).toBeInTheDocument()
  for (let i = 0; i < 25; i++) {
    fireEvent.click(screen.getByRole('button', { name: 'Další výměna →' }))
  }
  await waitFor(() => expect(screen.getByText(/26\/30/)).toBeInTheDocument())
  expect(api.getSavedPlayerMatchDetail).toHaveBeenCalledWith(
    'run', 'branch', 'A', 'event', 'final', 25, 25
  )
}

describe('replay identity cursor isolation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    branchContext.current = { run_id: 'run', branch_id: 'branch', saved_head_revision_id: 'rev' }
    useLongMatchFixture()
  })

  it('ignores an old pending match response delivered after navigating',async()=>{
    let resolveOld:((value:ReturnType<typeof result>)=>void)|undefined
    api.getSavedPlayerMatchDetail.mockImplementation((
      _run:string,_branch:string,_player:string,_event:string,matchId:string
    )=>matchId==='final'
      ?new Promise(resolve=>{resolveOld=resolve})
      :Promise.resolve(result({
        match:{...result().match,match_id:'short',scoreline:'3-0'}
      })))
    mount()
    await waitFor(()=>expect(api.getSavedPlayerMatchDetail).toHaveBeenCalledTimes(1))
    fireEvent.click(screen.getByRole('link',{name:'Switch match'}))
    expect(await screen.findByText(/3-0/)).toBeInTheDocument()
    await act(async()=>{resolveOld?.(result())})
    expect(screen.getByText(/3-0/)).toBeInTheDocument()
    expect(screen.queryByText(/3-2/)).not.toBeInTheDocument()
  })
  it.each([
    ['Switch match', 'run', 'branch', 'A', 'event', 'short'],
    ['Switch event', 'run', 'branch', 'A', 'second', 'final'],
    ['Switch player', 'run', 'branch', 'B', 'event', 'final'],
  ])('resets a page-2 cursor on %s with no stale page-2 request', async (
    link, runId, branchId, playerId, eventId, matchId
  ) => {
    mount()
    await seekSecondPage()
    fireEvent.click(screen.getByRole('link', { name: link }))
    await waitFor(() => expect(screen.getByText(/1\/2/)).toBeInTheDocument())
    expect(screen.queryByText(/V tomto úseku není výměna/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '← Předchozí výměna' })).toBeDisabled()
    expect(api.getSavedPlayerMatchDetail).toHaveBeenCalledWith(
      runId, branchId, playerId, eventId, matchId, 0, 25
    )
    expect(api.getSavedPlayerMatchDetail).not.toHaveBeenCalledWith(
      runId, branchId, playerId, eventId, matchId, 25, 25
    )
  })

  it('resets at first render when a new Run is selected, not after the old offset is fetched', async () => {
    mount()
    await seekSecondPage()
    branchContext.current = { run_id: 'other-run', branch_id: 'other-branch', saved_head_revision_id: 'other-rev' }
    fireEvent.click(screen.getByRole('link', { name: 'Switch Run' }))
    await waitFor(() => expect(screen.getByText(/1\/2/)).toBeInTheDocument())
    expect(api.getSavedPlayerMatchDetail).toHaveBeenCalledWith(
      'other-run', 'other-branch', 'A', 'event', 'final', 0, 25
    )
    expect(api.getSavedPlayerMatchDetail).not.toHaveBeenCalledWith(
      'other-run', 'other-branch', 'A', 'event', 'final', 25, 25
    )
  })

  it.each([
    ['Branch', 'branch-next', 'rev-next'],
    ['Saved Revision', 'branch', 'rev-next'],
  ])('blocks the old scoped URL on %s change without reading the old page of the new HEAD', async (
    _label, nextBranch, nextHead
  ) => {
    const view = mount()
    await seekSecondPage()
    const previousCallCount = api.getSavedPlayerMatchDetail.mock.calls.length
    branchContext.current = { run_id: 'run', branch_id: nextBranch, saved_head_revision_id: nextHead }
    await act(async () => { view.refreshBranch() })
    expect(await screen.findByRole('alert')).toHaveTextContent('Odkaz patří jiné Branch nebo Saved HEAD')
    expect(api.getSavedPlayerMatchDetail).toHaveBeenCalledTimes(previousCallCount)
    fireEvent.click(screen.getByRole('button', { name: 'Přejít na aktuální zdroj' }))
    await waitFor(() => expect(screen.getByText(/1\/2/)).toBeInTheDocument())
    const newScopeCalls = api.getSavedPlayerMatchDetail.mock.calls.slice(previousCallCount)
    expect(newScopeCalls).toContainEqual(['run', nextBranch, 'A', 'event', 'final', 0, 25])
    expect(newScopeCalls).not.toContainEqual(['run', nextBranch, 'A', 'event', 'final', 25, 25])
  })
  it('retries an interrupted archived match read without altering its cursor or Saved HEAD',async()=>{
    api.getSavedPlayerMatchDetail.mockRejectedValueOnce(new Error('offline'))
    mount()
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.queryByText('Championship')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Obnovit zápas / archiv'}))
    expect(await screen.findByText('Championship')).toBeInTheDocument()
    expect(api.getSavedPlayerMatchDetail).toHaveBeenLastCalledWith(
      'run','branch','A','event','final',0,25)
  })

})

describe('archived player rally navigation (mocked API, not real browser)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    branchContext.current = { run_id: 'run', branch_id: 'branch', saved_head_revision_id: 'rev' }
    useLongMatchFixture()
    localStorage.removeItem('squash-engine-language-v1')
  })
  it('restores scoped rally from URL with only its actual 25-frame page', async () => {
    mount('/admin/runs/run/people/A/matches/event/final?tab=career&careerSeason=2&careerPage=1&careerQ=Brno&careerOutcome=win&replayBranch=branch&replayHead=rev&rally=27')
    expect(await screen.findByText(/27\/30/)).toBeInTheDocument()
    expect(api.getSavedPlayerMatchDetail).toHaveBeenCalledWith('run','branch','A','event','final',25,25)
    expect(api.getSavedPlayerMatchDetail).not.toHaveBeenCalledWith('run','branch','A','event','final',0,25)
    expect(screen.getByRole('link',{name:/Zpět na profil hráče/})).toHaveAttribute('href',
      '/admin/runs/run/people/A?tab=career&careerSeason=2&careerPage=1&careerOutcome=win&careerQ=Brno')
    fireEvent.click(screen.getByRole('button',{name:'Test English'}))
    expect(screen.getByText(/Rally 27\/30/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Last rally'})).toBeEnabled()
    expect(api.getSavedPlayerMatchDetail).toHaveBeenCalledTimes(1)
  })
  it('rejects invalid and unscoped deep links without reading the archive', async () => {
    mount('/admin/runs/run/people/A/matches/event/final?rally=26')
    expect(screen.getByRole('alert')).toHaveTextContent('Odkaz patří jiné Branch')
    expect(api.getSavedPlayerMatchDetail).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button',{name:'Přejít na aktuální zdroj'}))
    expect(await screen.findByText(/1\/30/)).toBeInTheDocument()
  })
  it('rejects malicious/noncanonical rally without an API call', async () => {
    mount('/admin/runs/run/people/A/matches/event/final?replayBranch=branch&replayHead=rev&rally=001')
    expect(screen.getByRole('alert')).toHaveTextContent('Neplatné číslo výměny')
    expect(api.getSavedPlayerMatchDetail).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button',{name:'Otevřít aktuální první výměnu'}))
    expect(await screen.findByText(/1\/30/)).toBeInTheDocument()
  })
  it('first, last, numeric jump and loaded-page timeline share one verified source', async () => {
    mount()
    expect(await screen.findByText(/1\/30/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Poslední výměna'}))
    expect(await screen.findByText(/30\/30/)).toBeInTheDocument()
    fireEvent.click(screen.getByText(/Přehled uložených výměn/))
    const item=screen.getByRole('button',{name:/Výměna 27/})
    fireEvent.click(item)
    expect(await screen.findByText(/27\/30/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:/Výměna 27/})).toHaveAttribute('aria-current','step')
    fireEvent.change(screen.getByRole('spinbutton',{name:'Číslo archivované výměny'}),{target:{value:'31'}})
    expect(screen.getByRole('button',{name:'Přejít'})).toBeDisabled()
    fireEvent.change(screen.getByRole('spinbutton',{name:'Číslo archivované výměny'}),{target:{value:'1'}})
    fireEvent.click(screen.getByRole('button',{name:'Přejít'}))
    expect(await screen.findByText(/1\/30/)).toBeInTheDocument()
  })
  it('out-of-range bookmarked page does not poison a legitimate final page after recovery', async () => {
    mount('/admin/runs/run/people/A/matches/event/final?replayBranch=branch&replayHead=rev&rally=60')
    expect(await screen.findByRole('alert')).toHaveTextContent('Požadovaná výměna v tomto archivu neexistuje')
    expect(api.getSavedPlayerMatchDetail).toHaveBeenCalledWith('run','branch','A','event','final',50,25)
    fireEvent.click(screen.getByRole('button',{name:'První platná výměna'}))
    expect(await screen.findByText(/1\/30/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Poslední výměna'}))
    expect(await screen.findByText(/30\/30/)).toBeInTheDocument()
    expect(screen.queryByText('Detail neodpovídá vybrané uložené revizi')).not.toBeInTheDocument()
  })
  it('rejects a foreign scoped bookmark after a HEAD change, even for same match', async () => {
    branchContext.current = { run_id:'run',branch_id:'branch',saved_head_revision_id:'rev-next' }
    mount('/admin/runs/run/people/A/matches/event/final?replayBranch=branch&replayHead=rev&rally=26')
    expect(screen.getByRole('alert')).toHaveTextContent('Odkaz patří jiné Branch')
    expect(api.getSavedPlayerMatchDetail).not.toHaveBeenCalled()
  })

  it('rejects repeated replay authority keys before reading any archive', async () => {
    mount('/admin/runs/run/people/A/matches/event/final?replayBranch=branch&replayHead=rev&rally=26&rally=1')
    expect(screen.getByRole('alert')).toHaveTextContent('Nejednoznačný odkaz')
    expect(api.getSavedPlayerMatchDetail).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', {name:'Otevřít aktuální zdroj'}))
    expect(await screen.findByText(/1\/30/)).toBeInTheDocument()
  })
  it('does not expose names from a foreign identity source even if other keys match', async () => {
    api.getSavedHomePlayerIdentities.mockImplementation(async (_r:string,_b:string,ids:string[])=>({
      run_id:'run',branch_id:'branch',saved_revision_id:'rev',
      source:'wrong_source',requested_ids:ids,
      players:ids.map(id=>({player_id:id,display_name:'UNVERIFIED '+id})),
    }))
    mount()
    expect(await screen.findByText('Championship')).toBeInTheDocument()
    expect(screen.queryByText(/UNVERIFIED/)).not.toBeInTheDocument()
    expect(screen.getByText(/A porazil B/)).toBeInTheDocument()
  })
  it('makes no replay when the canonical result has no saved rally archive', async () => {
    api.getSavedPlayerMatchDetail.mockResolvedValue(result({
      replay_status:'unavailable', total_rallies:0, has_more:false,
      player_a_id:null,player_b_id:null, rallies:[],
      match:{...result().match, completion:'walkover', scoreline:'W/O'},
    }))
    mount()
    expect(await screen.findByText(/Ověřený archiv výměn není/)).toBeInTheDocument()
    expect(screen.getByText(/Výsledek kontumací/)).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Poslední výměna'})).not.toBeInTheDocument()
  })
})
