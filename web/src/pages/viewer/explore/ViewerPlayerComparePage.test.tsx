import {cleanup, fireEvent, render, screen, waitFor} from '@testing-library/react'
import {QueryClient, QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter} from 'react-router-dom'
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {ViewerH2HPage, ViewerPlayerComparisonPage} from './ViewerPlayerComparePage'

const mocks = vi.hoisted(()=>({
  getRunPlayerDetail: vi.fn(),
  listRunPlayers: vi.fn(),
  language: 'en',
  runId: 'run-a'
}))
vi.mock('../../../api/client',()=>({
  getRunPlayerDetail:mocks.getRunPlayerDetail,
  listRunPlayers:mocks.listRunPlayers
}))
vi.mock('../../../viewer/useActiveViewerRunId',()=>({
  useActiveViewerRunId:()=>mocks.runId
}))
vi.mock('../../../viewer/ViewerContext',()=>({
  useViewerContext:()=>({selectedSeason:0,selectedWeek:1})
}))
vi.mock('../../../i18n/LanguageContext',()=>({
  useLanguage:()=>({language:mocks.language})
}))

function makePlayer(id:string, overall=80) {
  return {
    player_id:id,name:'Player '+id,country_code:'EGY',age:25,
    source_type:'planner_generated',quality_band:'elite',is_top_band:true,
    overall,technique:80,movement:81,physical:82,mental:83,
    override_id:null,origin_source_type:'planner_generated',
    origin_quality_band:'elite',origin_override_id:null,origin_season:2025
  }
}
function mount(path='/viewer/compare?playerA=player-1&playerB=player-900', h2h=false) {
  const queryClient=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}})
  const app=(<QueryClientProvider client={queryClient}>
    <MemoryRouter initialEntries={[path]}>
      {h2h ? <ViewerH2HPage /> : <ViewerPlayerComparisonPage />}
    </MemoryRouter>
  </QueryClientProvider>)
  const view=render(app)
  return {...view,queryClient}
}
beforeEach(()=>{
  mocks.runId='run-a'
  mocks.language='en'
  mocks.getRunPlayerDetail.mockReset()
  mocks.listRunPlayers.mockReset()
  mocks.listRunPlayers.mockResolvedValue({
    run_id:'run-a',total:1000,limit:50,offset:0,
    players:[makePlayer('player-1')]
  })
  mocks.getRunPlayerDetail.mockImplementation(async (_run:string,id:string)=>
    makePlayer(id,id==='player-900'?76:80))
})
afterEach(()=>cleanup())

describe('Viewer exact player comparison',()=>{
  it('loads player #900 by exact GET, not by scanning the first 50',async()=>{
    mount()
    expect(await screen.findByText('Player player-900')).toBeInTheDocument()
    expect(mocks.getRunPlayerDetail).toHaveBeenCalledWith('run-a','player-1')
    expect(mocks.getRunPlayerDetail).toHaveBeenCalledWith('run-a','player-900')
    expect(mocks.listRunPlayers).toHaveBeenCalledWith('run-a',{limit:50,offset:0})
    expect(mocks.listRunPlayers).toHaveBeenCalledTimes(1)
    expect(screen.getByText('Power Rating difference')).toBeInTheDocument()
    expect(screen.getByText('+4')).toBeInTheDocument()
  })

  it('does not fetch when exact IDs are missing or identical',async()=>{
    const a=mount('/viewer/compare?playerA=same&playerB=same')
    expect(await screen.findByRole('alert')).toHaveTextContent('different')
    expect(mocks.getRunPlayerDetail).not.toHaveBeenCalled()
    a.unmount()
    mount('/viewer/compare?playerA=only')
    expect(await screen.findByRole('alert')).toHaveTextContent('different')
    expect(mocks.getRunPlayerDetail).not.toHaveBeenCalled()
  })

  it('rejects a response with foreign player identity instead of showing false comparison',async()=>{
    mocks.getRunPlayerDetail.mockImplementation(async (_run:string,id:string)=>
      makePlayer(id==='player-900'?'foreign-player':id))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('mismatched player identity')
    expect(screen.queryByText('Power Rating difference')).not.toBeInTheDocument()
    expect(screen.queryByText('+4')).not.toBeInTheDocument()
    expect(screen.queryByText('Player foreign-player')).not.toBeInTheDocument()
  })

  it('preserves a complete exact comparison when the first-50 sample endpoint fails',async()=>{
    mocks.listRunPlayers.mockRejectedValueOnce(new Error('sample unavailable'))
    mount()
    expect(await screen.findByText('Player player-900')).toBeInTheDocument()
    expect(screen.getByText('Player discovery sample is temporarily unavailable.')).toBeInTheDocument()
    expect(mocks.getRunPlayerDetail).toHaveBeenCalledTimes(2)
  })

  it('requires explicit form submission and suppresses old results while editing',async()=>{
    mount('/viewer/compare')
    expect(mocks.getRunPlayerDetail).not.toHaveBeenCalled()
    const a=screen.getByLabelText('First player ID')
    const b=screen.getByLabelText('Second player ID')
    fireEvent.change(a,{target:{value:'player-1'}})
    fireEvent.change(b,{target:{value:'player-900'}})
    expect(mocks.getRunPlayerDetail).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button',{name:'Compare players'}))
    expect(await screen.findByText('Player player-900')).toBeInTheDocument()
    fireEvent.change(b,{target:{value:'player-901'}})
    expect(screen.getByText(/Apply the changed player IDs/)).toBeInTheDocument()
    expect(screen.queryByText('Player player-900')).not.toBeInTheDocument()
    expect(mocks.getRunPlayerDetail).toHaveBeenCalledTimes(2)
    fireEvent.click(screen.getByRole('button',{name:'Compare players'}))
    expect(await screen.findByText('Player player-901')).toBeInTheDocument()
    expect(mocks.getRunPlayerDetail).toHaveBeenCalledWith('run-a','player-901')
    fireEvent.click(screen.getByRole('button',{name:'Clear comparison'}))
    expect((screen.getByLabelText('First player ID') as HTMLInputElement).value).toBe('')
    expect((screen.getByLabelText('Second player ID') as HTMLInputElement).value).toBe('')
    expect(screen.queryByText('Player player-901')).not.toBeInTheDocument()
  })

  it('uses the selected Run in query keys so previous Run detail cannot leak',async()=>{
    const view=mount()
    expect(await screen.findByText('Player player-900')).toBeInTheDocument()
    mocks.runId='run-b'
    mocks.getRunPlayerDetail.mockImplementation(async (_run:string,id:string)=>
      makePlayer(id,67))
    view.rerender(<QueryClientProvider client={view.queryClient}>
      <MemoryRouter initialEntries={['/viewer/compare?playerA=player-1&playerB=player-900']}>
        <ViewerPlayerComparisonPage />
      </MemoryRouter>
    </QueryClientProvider>)
    await waitFor(()=>expect(mocks.getRunPlayerDetail).toHaveBeenCalledWith('run-b','player-900'))
    expect(await screen.findByText('Player player-900')).toBeInTheDocument()
    expect(screen.queryByText('+4')).not.toBeInTheDocument()
  })

  it('remains read-only: clicking comparison only issues exact GETs',async()=>{
    mount()
    await screen.findByText('Player player-900')
    expect(mocks.getRunPlayerDetail).toHaveBeenCalledTimes(2)
    expect(mocks.listRunPlayers).toHaveBeenCalledTimes(1)
    expect(screen.getByText(/not match history or predicted odds/)).toBeInTheDocument()
  })
})


describe('Comparison CS/EN copy (mocked language and GET boundaries)', () => {
  it('translates Czech page, exact cards and differences while retaining stored identity and zero values', async () => {
    mocks.language = 'cs'
    mocks.getRunPlayerDetail.mockImplementation(async (_run: string, id: string) => ({
      ...makePlayer(id, 0), name: id === 'player-1' ? 'Original Name' : 'Druhé Jméno', age: 0
    }))
    mount()
    expect(await screen.findByText('Original Name')).toBeInTheDocument()
    expect(screen.getByRole('heading', {name: 'Porovnání hráčů'})).toBeInTheDocument()
    expect(screen.getByRole('heading', {name: 'Hráč A'})).toBeInTheDocument()
    expect(screen.getByText('Rozdíl herní síly')).toBeInTheDocument()
    expect(screen.getAllByText('0').length).toBeGreaterThan(0)
    expect(screen.getAllByText('elite')).toHaveLength(2)
    expect(screen.getByRole('link', {name: 'Vyhledat Original Name'})).toHaveAttribute('href', '/viewer/search?q=player-1')
    expect(screen.getByRole('button', {name: 'Porovnat hráče'})).toBeInTheDocument()
    expect(screen.queryByText('Power Rating difference')).not.toBeInTheDocument()
  })

  it('switches loaded comparison labels without reloading GET data or changing the selected IDs', async () => {
    const view = mount()
    await screen.findByText('Player player-900')
    mocks.language = 'cs'
    view.rerender(<QueryClientProvider client={view.queryClient}>
      <MemoryRouter initialEntries={['/viewer/compare?playerA=player-1&playerB=player-900']}>
        <ViewerPlayerComparisonPage />
      </MemoryRouter>
    </QueryClientProvider>)
    expect(screen.getByRole('heading', {name: 'Porovnání hráčů'})).toBeInTheDocument()
    expect(screen.getByLabelText('ID prvního hráče')).toHaveValue('player-1')
    expect(screen.getByText('Rozdíl herní síly')).toBeInTheDocument()
    expect(screen.getByText('+4')).toBeInTheDocument()
    expect(mocks.getRunPlayerDetail).toHaveBeenCalledTimes(2)
    expect(mocks.listRunPlayers).toHaveBeenCalledTimes(1)
  })

  it('localizes the no-Run state and issues no GET', () => {
    mocks.language = 'cs'
    mocks.runId = ''
    mount()
    expect(screen.getByText('Pro tento Run zatím nejsou dostupná data.')).toBeInTheDocument()
    expect(mocks.getRunPlayerDetail).not.toHaveBeenCalled()
    expect(mocks.listRunPlayers).not.toHaveBeenCalled()
  })

  it('localizes the H2H boundary and failed discovery without losing exact comparison', async () => {
    mocks.language = 'cs'
    mocks.listRunPlayers.mockRejectedValue(new Error('unavailable'))
    mount('/viewer/h2h?playerA=player-1&playerB=player-900', true)
    await screen.findByText('Player player-900')
    expect(screen.getByText('Čtecí porovnání atributů hráčů, nikoliv autoritativní historie vzájemných zápasů.')).toBeInTheDocument()
    expect(screen.getByText('Ukázkový výběr hráčů je dočasně nedostupný.')).toBeInTheDocument()
    expect(screen.getByText('Rozdíl herní síly')).toBeInTheDocument()
  })
})
