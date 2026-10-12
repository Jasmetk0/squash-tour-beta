import { render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RunWorldPage } from './RunWorldPage'
import { worldFixture } from './runWorldFixture'

const api=vi.hoisted(()=>({getRunPackageState:vi.fn(),getSavedPlayersInventory:vi.fn(),
  getSavedRevision:vi.fn(),listSavedRevisionHistory:vi.fn()}))
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

function historicalDetail(
  revisionId:string,name:string,origin='branch-a',selected='branch-a',missing=false
){
  const f=worldFixture()
  if(f.state){
    f.state.branch_id=origin
    const country=(f.state.entities as Record<string,unknown>[])[1].payload as Record<string,unknown>
    country.name=name
  }
  return {
    run_id:'run-a',branch_id:selected,revision_id:revisionId,
    revision_branch_id:origin,is_shared_revision:origin!==selected,
    payload_schema_version:'run_saved_revision_v1',
    payload:{
      run:{run_id:'run-a'},branch:{branch_id:origin},
      content:missing?{}:{run_package_state:{fingerprint:f.fingerprint,state:f.state}}
    }
  }
}

describe('Run-owned World overview navigation',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    context.branch.run_id='run-a'
    context.branch.branch_id='branch-a'
    context.branch.saved_head_revision_id='head-a'
    context.time.mode='present'
    context.language='en'
    api.getRunPackageState.mockResolvedValue(worldFixture())
    api.listSavedRevisionHistory.mockImplementation(async (run:string,branch:string)=>({
      run_id:run,branch_id:branch,saved_head_revision_id:context.branch.saved_head_revision_id,
      saved_revisions:['rev-old','rev-new','rev-shared'].map((id,i)=>({
        revision_id:id,sequence:i+1,is_shared_revision:false,revision_branch_id:branch,
        is_branch_head:false
      })),total_count:3,has_more_older:false,next_before_sequence:null
    }))
    api.getSavedRevision.mockImplementation(async (_r:string,b:string,id:string)=>historicalDetail(id,'Old Czechia','branch-a',b))
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
    expect(screen.getByLabelText('Country rating history')).toHaveTextContent('Fallback authored year: 2020')
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
    expect(screen.getByRole('alert')).toHaveTextContent('Simulation checkpoint')
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
    expect(screen.getByRole('alert')).toHaveTextContent('Simulation checkpoint')
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })
  it('does not leak a foreign branch into World',()=>{
    context.branch.run_id='foreign'
    mountWorld('/admin/runs/run-a/world')
    expect(screen.getByRole('alert')).toHaveTextContent('Select a valid Branch')
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })
  it('reads two distinct persisted World revisions, not current Saved HEAD or current World',async()=>{
    api.getSavedRevision.mockImplementation(async(_r:string,b:string,id:string)=>
      historicalDetail(id,id==='rev-old'?'Old Czechia':'New Czechia','branch-a',b))
    mountWorld('/admin/runs/run-a/world?year=2000&revision=rev-old')
    const table=await screen.findByRole('table',{name:'Run World countries'})
    expect(table).toHaveTextContent('Old Czechia')
    expect(table).not.toHaveTextContent('New Czechia')
    expect(screen.getByText(/Origin Branch/)).toHaveTextContent('branch-a')
    expect(api.getRunPackageState).not.toHaveBeenCalled()
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'World Saved Revision'}),'rev-new')
    await waitFor(()=>expect(screen.getByRole('table',{name:'Run World countries'})).toHaveTextContent('New Czechia'))
    expect(screen.getByRole('table',{name:'Run World countries'})).not.toHaveTextContent('Old Czechia')
    expect(api.getSavedRevision).toHaveBeenCalledWith('run-a','branch-a','rev-new')
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })
  it('reads a shared ancestor through selected Branch reachability without rewriting owner',async()=>{
    context.branch.branch_id='branch-b'
    context.branch.saved_head_revision_id='head-b'
    api.getSavedRevision.mockResolvedValue(historicalDetail('rev-shared','Shared Historical Czechia','branch-a','branch-b'))
    mountWorld('/admin/runs/run-a/world?revision=rev-shared')
    expect(await screen.findByRole('table',{name:'Run World countries'})).toHaveTextContent('Shared Historical Czechia')
    expect(screen.getByText(/Origin Branch/)).toHaveTextContent('branch-a')
    expect(screen.getByText(/shared ancestor/)).toBeInTheDocument()
    expect(api.getSavedRevision).toHaveBeenCalledWith('run-a','branch-b','rev-shared')
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })
  it('disables current Saved HEAD players in historical country detail',async()=>{
    mountWorld('/admin/runs/run-a/world/countries/CZE?revision=rev-old&tab=players&year=2005')
    expect(await screen.findByRole('heading',{name:'Historical player roster'})).toBeInTheDocument()
    expect(screen.getByLabelText('Historical country roster unavailable')).toHaveTextContent(
      'Current saved players are never substituted'
    )
    expect(api.getSavedPlayersInventory).not.toHaveBeenCalled()
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })
  it('reports a missing historical World component or unreachable revision without fallback',async()=>{
    api.getSavedRevision.mockResolvedValue(historicalDetail('rev-old','Invisible','branch-a','branch-a',true))
    mountWorld('/admin/runs/run-a/world?revision=rev-old')
    expect(await screen.findByRole('alert')).toHaveTextContent('has no saved Run World component')
    expect(screen.queryByRole('table',{name:'Run World countries'})).not.toBeInTheDocument()
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })
  it('hides even cached historical World immediately when simulation checkpoint is selected',async()=>{
    const view=mountWorld('/admin/runs/run-a/world?revision=rev-old')
    expect(await screen.findByRole('table',{name:'Run World countries'})).toHaveTextContent('Old Czechia')
    context.time.mode='checkpoint'
    view.refresh()
    expect(screen.getByRole('alert')).toHaveTextContent('Simulation checkpoint')
    expect(screen.queryByRole('table',{name:'Run World countries'})).not.toBeInTheDocument()
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })


  it('shows saved hosted Editions from immutable HEAD, never template country or mutable draft',async()=>{
    const fixture=worldFixture()
    const entities=fixture.state!.entities as Record<string,unknown>[]
    ;(fixture.state!.package_versions as Record<string,unknown>[]).push({
      package_id:'calendar-2000-2001',package_type:'Calendar'
    })
    entities.push(
      {source_package_id:'calendar-2000-2001',source_entity_id:'calendar.metadata',
        entity_kind:'calendar.metadata.v1',payload:{season:'2000/2001'}},
      {source_package_id:'calendar-2000-2001',source_entity_id:'edition-1',
        entity_kind:'calendar.event.v1',payload:{event_id:'edition-1',
          season:'2000/2001',season_week:5,event_name:'Brno World Open',
          host_country:'CZE',host_city:'Brno',status:'planned',
          template_snapshot:{host_country:'USA'}}}
    )
    api.getSavedRevision.mockResolvedValue({
      ...historicalDetail('head-a','Saved Czechia'),
      payload:{run:{run_id:'run-a'},branch:{branch_id:'branch-a'},content:{
        run_package_state:{fingerprint:fixture.fingerprint,state:fixture.state}}}
    })
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=tournaments&year=2020')
    expect(await screen.findByRole('table',{name:'Country tournament editions 2000/2001'}))
      .toHaveTextContent('Brno World Open')
    const panel=screen.getByLabelText('Country Run-owned tournaments')
    expect(panel).toHaveTextContent('head-a')
    expect(panel).toHaveTextContent('Brno (CZE)')
    expect(panel).not.toHaveTextContent('USA')
    expect(api.getSavedRevision).toHaveBeenCalledWith('run-a','branch-a','head-a')
  })
  it('does not substitute present saved HEAD or mutable World for a historical Calendar',async()=>{
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=tournaments&revision=rev-old')
    expect(await screen.findByLabelText('Country Run-owned tournaments')).toHaveTextContent(
      'This saved revision has no Calendar Package')
    expect(api.getRunPackageState).not.toHaveBeenCalled()
    expect(api.getSavedRevision).toHaveBeenCalledWith('run-a','branch-a','rev-old')
    expect(screen.queryByRole('link',{name:'Brno World Open'})).not.toBeInTheDocument()
  })
  it('reports absent Saved HEAD for tournaments without borrowing unsaved packages',async()=>{
    context.branch.saved_head_revision_id=''
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=tournaments')
    expect(await screen.findByLabelText('Country Run-owned tournaments'))
      .toHaveTextContent('No Saved Revision is available')
    expect(api.getSavedRevision).not.toHaveBeenCalled()
  })

})
