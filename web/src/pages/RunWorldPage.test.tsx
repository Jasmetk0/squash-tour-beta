import { render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RunWorldPage } from './RunWorldPage'
import { worldFixture } from './runWorldFixture'

const api=vi.hoisted(()=>({getRunPackageState:vi.fn(),getSavedPlayersInventory:vi.fn()}))
const context=vi.hoisted(()=>({
  branch:{run_id:'run-a',branch_id:'branch-a',saved_head_revision_id:'head-a',display_name:'Timeline 1'},
  time:{mode:'present',isLoading:false,error:null},
  language:'en'
}))
vi.mock('../api/client',()=>api)
vi.mock('../admin/AdminBranchContext',()=>({
  useAdminBranch:()=>({selectedBranch:context.branch,isLoading:false,error:null})
}))
vi.mock('../admin/AdminTimeContext',()=>({useAdminTime:()=>context.time}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:context.language})}))

function mountWorld(path:string):{refresh:()=>void} {
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
  const wrap=()=> <QueryClientProvider client={client}>
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/runs/:runId/world" element={<RunWorldPage/>}/>
        <Route path="/admin/runs/:runId/world/countries/:countryCode" element={<RunWorldPage/>}/>
      </Routes>
    </MemoryRouter>
  </QueryClientProvider>
  const mounted=render(wrap())
  return {refresh:()=>mounted.rerender(wrap())}
}

type CountryFilters={
  search:string;country_code:string;status_filter:string;include_prepared:boolean
  offset:number;limit:number
}
function savedCountryResponse(filters:CountryFilters,head='head-a'){
  return {
    schema_version:'saved_players_inventory.v1',
    run_id:'run-a',branch_id:'branch-a',saved_revision_id:head,
    source:'selected_branch_saved_revision',time_context:'present',
    ranking_week_ordinal:null,...filters,
    total:26,has_more:filters.offset+filters.limit<26,
    players:[{
      player_id:filters.offset===0?'cze-p1':'cze-p26',
      display_name:filters.offset===0?'Czech Player One':'Czech Player Twenty Six',
      country_code:'CZE',identity_source:'initial_world',
      status:'active',age:21,ovr:73,potential_ovr:90,
      ranking_status:'unpublished',rank:null
    }]
  }
}

describe('Run-owned World overview navigation',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    context.branch.run_id='run-a'
    context.branch.saved_head_revision_id='head-a'
    context.time.mode='present'
    context.language='en'
    api.getRunPackageState.mockResolvedValue(worldFixture())
    api.getSavedPlayersInventory.mockImplementation(async (_run:string,_branch:string,head:string,filters:CountryFilters)=>savedCountryResponse(filters,head))
  })
  it('displays incomplete population, filters copied countries and links into six-tab detail preserving year/search',async()=>{
    mountWorld('/admin/runs/run-a/world?year=2000')
    expect(await screen.findByText('Saved FIFA Earth')).toBeInTheDocument()
    expect(screen.getByLabelText('World summary metrics')).toHaveTextContent('Incomplete')
    expect(screen.getByLabelText('World summary metrics')).toHaveTextContent('341,250,000')
    expect(screen.getByRole('table',{name:'Run World countries'})).toHaveTextContent('Czechia')
    expect(screen.getByRole('table',{name:'Run World countries'})).toHaveTextContent('United States')
    await userEvent.type(screen.getByRole('searchbox',{name:'Search Run World countries'}),'cze')
    await waitFor(()=>expect(screen.getByRole('table',{name:'Run World countries'})).not.toHaveTextContent('United States'))
    expect(screen.getByRole('link',{name:'Czechia (CZE)'})).toHaveAttribute(
      'href',expect.stringContaining('q=cze')
    )
    expect(api.getRunPackageState).toHaveBeenCalledWith('run-a','branch-a')
  })
  it('shows country tabs, source fields and a reversible return link',async()=>{
    mountWorld('/admin/runs/run-a/world/countries/CZE?year=2000&q=cze')
    expect(await screen.findByRole('heading',{name:/Czechia/})).toBeInTheDocument()
    expect(screen.getByRole('navigation',{name:'Country detail sections'}).querySelectorAll('a')).toHaveLength(6)
    expect(screen.getByText('EUROPE_CENTRAL')).toBeInTheDocument()
    expect(screen.getByRole('link',{name:/Back to countries/})).toHaveAttribute(
      'href','/admin/runs/run-a/world?year=2000&q=cze'
    )
    expect(api.getRunPackageState).toHaveBeenCalledTimes(1)
  })

  it('shows only authored population anchors and preserves tab/filter when inspecting another year',async()=>{
    mountWorld('/admin/runs/run-a/world/countries/CZE?year=2010&tab=population&q=cz')
    expect(await screen.findByRole('heading',{name:'Population history'})).toBeInTheDocument()
    expect(screen.getByLabelText('Country population history')).toHaveTextContent('Nearest authored year')
    const years=screen.getByRole('table',{name:'Authored population timeline'})
    expect(years).toHaveTextContent('2000')
    expect(years).toHaveTextContent('2020')
    expect(within(years).queryByRole('link',{name:'2010'})).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('link',{name:'2020'}))
    expect(screen.getByLabelText('Country population history')).toHaveTextContent('Selected year: 2020')
    expect(screen.getByRole('link',{name:/Back to countries/})).toHaveAttribute(
      'href','/admin/runs/run-a/world?year=2020&q=cz'
    )
  })
  it('shows six country rating evidence rows without fabricating legacy yearly rating history',async()=>{
    mountWorld('/admin/runs/run-a/world/countries/CZE?year=2000&tab=ratings')
    const panel=await screen.findByLabelText('Country rating history')
    expect(panel).toHaveTextContent('History of six country ratings')
    expect(screen.getAllByText('legacy scalar — no year attribution').length).toBeGreaterThan(0)
    expect(screen.getByText(/No source-evidenced rating timeline exists/)).toBeInTheDocument()
    expect(screen.queryByRole('table',{name:'Authored country rating years'})).not.toBeInTheDocument()
  })

  it('shows source-evidenced V2 rating trend, source IDs, and selected-year fallback provenance',async()=>{
    const fixture=worldFixture()
    const row=(fixture.state!.entities as Record<string,unknown>[])[1].payload as Record<string,unknown>
    row.rating_scale='country_ratings_1_10.v2'
    const keys=['squash_popularity','squash_access','development_quality',
      'competition_quality','elite_support','squash_tradition']
    const evidence=Object.fromEntries(keys.map(key=>[key,{
      value:key==='elite_support'?7.2:6.4,method:'sourced_estimate',
      confidence:'high',source_ids:['source-v2'],
      observation_ids:['source-v2#row1'],rationale:'Independent evidence',
      anchor_years:[2020]
    }]))
    row.rating_history={reference_year:2020,data_cutoff:'2026-01-01',
      years:{'2020':{historical_entity:'Czechia',territory_mapping_note:'Same boundaries',ratings:evidence}}}
    api.getRunPackageState.mockResolvedValue(fixture)
    mountWorld('/admin/runs/run-a/world/countries/CZE?year=2019&tab=ratings&q=cze')
    expect(await screen.findByRole('heading',{name:'History of six country ratings'})).toBeInTheDocument()
    expect(screen.getByLabelText('Country rating history')).toHaveTextContent('Nearest authored year: 2020')
    expect(screen.getByRole('table',{name:'Authored country rating years'})).toHaveTextContent('2020')
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Country rating trend field'}),'elite_support')
    expect(screen.getByRole('table',{name:'Authored country rating years'})).toHaveTextContent('7.2')
    const details=screen.getAllByText('Value provenance details')
    await userEvent.click(details[0])
    expect(screen.getAllByText('source-v2').length).toBeGreaterThan(0)
    expect(screen.getAllByText('source-v2#row1').length).toBeGreaterThan(0)
    expect(screen.getByRole('link',{name:/Back to countries/})).toHaveAttribute(
      'href','/admin/runs/run-a/world?year=2019&q=cze')
  })

  it('hides even cached present World facts as soon as a historical checkpoint becomes selected',async()=>{
    const view=mountWorld('/admin/runs/run-a/world')
    expect(await screen.findByText('Saved FIFA Earth')).toBeInTheDocument()
    expect(api.getRunPackageState).toHaveBeenCalledTimes(1)
    context.time.mode='checkpoint'
    view.refresh()
    expect(screen.getByRole('alert')).toHaveTextContent('Historical checkpoint selected')
    expect(screen.queryByText('Saved FIFA Earth')).not.toBeInTheDocument()
    expect(api.getRunPackageState).toHaveBeenCalledTimes(1)
  })


  it('reads actual country roster only from selected immutable Saved HEAD and allows server paging',async()=>{
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=players&year=2020')
    expect(await screen.findByRole('heading',{name:'Saved country players'})).toBeInTheDocument()
    expect(screen.getByLabelText('Run World canonical country players')).toHaveTextContent(
      'NOT a historical roster for World year 2020'
    )
    expect(await screen.findByRole('link',{name:'Czech Player One'})).toHaveAttribute(
      'href','/admin/runs/run-a/people/cze-p1'
    )
    expect(api.getSavedPlayersInventory).toHaveBeenCalledWith(
      'run-a','branch-a','head-a',expect.objectContaining({
        country_code:'CZE',include_prepared:false,offset:0,limit:25
      })
    )
    await userEvent.click(screen.getByRole('button',{name:'Next →'}))
    expect(await screen.findByRole('link',{name:'Czech Player Twenty Six'})).toBeInTheDocument()
    expect(api.getSavedPlayersInventory).toHaveBeenLastCalledWith(
      'run-a','branch-a','head-a',expect.objectContaining({offset:25,country_code:'CZE'})
    )
    await userEvent.click(screen.getByRole('checkbox',{name:/Explicitly include saved prepared prospects/}))
    await waitFor(()=>expect(api.getSavedPlayersInventory).toHaveBeenLastCalledWith(
      'run-a','branch-a','head-a',expect.objectContaining({offset:0,include_prepared:true})
    ))
    expect(screen.getByRole('link',{name:'Czech Player One'})).toBeInTheDocument()
  })
  it('fails closed on foreign country or foreign Saved HEAD response without leaking a player link',async()=>{
    api.getSavedPlayersInventory.mockImplementation(async(_r:string,_b:string,_h:string,f:CountryFilters)=>({
      ...savedCountryResponse(f,'other-head'),
      players:[{...savedCountryResponse(f).players[0],country_code:'USA',display_name:'Foreign Player'}]
    }))
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=players')
    expect(await screen.findByRole('alert')).toHaveTextContent('Response scope does not match')
    expect(screen.queryByRole('link',{name:'Foreign Player'})).not.toBeInTheDocument()
    expect(screen.queryByRole('table',{name:'Saved country roster'})).not.toBeInTheDocument()
  })
  it('does not call players API or use legacy players without a Saved HEAD',async()=>{
    context.branch.saved_head_revision_id=''
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=players')
    expect(await screen.findByRole('heading',{name:'Saved country players'})).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('No authoritative Saved Revision')
    expect(api.getSavedPlayersInventory).not.toHaveBeenCalled()
    expect(screen.queryByRole('table',{name:'Saved country roster'})).not.toBeInTheDocument()
  })

  it('blocks present-only data at historical checkpoint without any current snapshot request',()=>{
    context.time.mode='checkpoint'
    mountWorld('/admin/runs/run-a/world')
    expect(screen.getByRole('alert')).toHaveTextContent('Historical checkpoint selected')
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })
  it('does not leak a foreign branch into World',()=>{
    context.branch.run_id='foreign'
    mountWorld('/admin/runs/run-a/world')
    expect(screen.getByRole('alert')).toHaveTextContent('Select a valid Branch')
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })
})
