import { render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RunWorldPage } from './RunWorldPage'
import { worldFixture } from './runWorldFixture'

const api=vi.hoisted(()=>({getRunPackageState:vi.fn(),getSavedPlayersInventory:vi.fn(),
  getSavedRevision:vi.fn(),listSavedRevisionHistory:vi.fn(),getRunCountryRecords:vi.fn(),
  getCountrySavedMatchRecords:vi.fn(),getCountryPlayerStandings:vi.fn(),ApiError:class extends Error{}}))
const context=vi.hoisted(()=>({
  branch:{run_id:'run-a',branch_id:'branch-a',saved_head_revision_id:'head-a',display_name:'Timeline 1'},
  time:{mode:'present',isLoading:false,error:null,presentSeason:0,presentWeek:61},
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


function savedMatchResult(revision:string,opts:{
  seasonIndex:number|null;resultKind:string;outcome:string;offset:number;limit:number
},rows:Record<string,unknown>[]=[] ,total=rows.length){
  return {
    schema_version:'country_saved_match_records.v1',source:'reachable_saved_revision',
    run_id:'run-a',branch_id:'branch-a',revision_branch_id:'branch-a',
    saved_revision_id:revision,country_code:'CZE',calendar_status:'ready',
    published_event_count:2,total_played_matches:30,total_walkovers:4,
    country_played_wins:18,country_played_losses:12,
    country_walkover_wins:2,country_walkover_losses:2,
    hosted_played_matches:6,hosted_walkovers:1,country_match_count:34,
    available_seasons:[0,1],
    season_index:opts.seasonIndex,result_kind:opts.resultKind,outcome:opts.outcome,
    filtered_match_count:total,offset:opts.offset,limit:opts.limit,
    has_more:opts.offset+opts.limit<total,matches:rows
  }
}
function matchRow(id:string,options:{
  season?:string;completion?:string;winnerCountry?:string;loserCountry?:string
}={}){
  return {
    event_id:'event-'+id,event_name:'Open '+id,
    season:options.season??'2000/2001',season_week:9,match_id:id,
    draw_type:'main',round_number:2,
    winner_player_id:'winner-'+id,winner_name:'Winner '+id,
    winner_country:options.winnerCountry??'CZE',
    loser_player_id:'loser-'+id,loser_name:'Loser '+id,
    loser_country:options.loserCountry??'EGY',host_country:'USA',
    completion:options.completion??'played',
    scoreline:options.completion==='walkover'?'W/O':'11-8, 11-9, 11-7'
  }
}


function standing(playerId:string,position:number,titles=0){
  return {player_id:playerId,player_name:'Player '+playerId,
    country_code:'CZE',position,titles,runner_up_finishes:0,final_appearances:titles,
    played_wins:2,played_losses:1,walkover_wins:0,walkover_losses:0}
}
function savedStandings(rev:string,offset=0,limit=25,players:ReturnType<typeof standing>[]=[],total=players.length){
  return {schema_version:'country_player_standings.v1',source:'reachable_saved_revision',
    run_id:'run-a',branch_id:'branch-a',revision_branch_id:'branch-a',
    saved_revision_id:rev,country_code:'CZE',calendar_status:'ready',
    published_event_count:1,country_titles:1,country_runner_up_finishes:0,
    country_played_wins:2,country_played_losses:1,
    country_walkover_wins:0,country_walkover_losses:0,
    total_players:total,offset,limit,has_more:offset+limit<total,players}
}

describe('Run-owned World overview navigation',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    context.branch.run_id='run-a'
    context.branch.branch_id='branch-a'
    context.branch.saved_head_revision_id='head-a'
    context.time.mode='present'
    context.time.presentSeason=0
    context.time.presentWeek=61
    context.language='en'
    api.getRunPackageState.mockResolvedValue(worldFixture())
    api.getCountryPlayerStandings.mockImplementation(async (
      _run:string,_branch:string,_country:string,rev:string,offset=0,limit=25
    )=>savedStandings(rev,offset,limit))
    api.getCountrySavedMatchRecords.mockImplementation(async (_run:string,_branch:string,_country:string,
      rev:string,opts:Parameters<typeof savedMatchResult>[1])=>savedMatchResult(rev,opts))
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
    const url=new URL(within(panel).getByRole('link',{name:'Brno World Open'})
      .getAttribute('href')!,'https://test.invalid')
    expect(url.pathname).toBe('/admin/runs/run-a/tour/calendar/edition-1')
    expect(url.searchParams.get('branch')).toBe('branch-a')
    expect(url.searchParams.get('revision')).toBe('head-a')
    expect(url.searchParams.get('season')).toBe('0')
    expect(url.searchParams.get('fromCountry')).toContain('tab=tournaments&year=2020')
    expect(api.getSavedRevision).toHaveBeenCalledWith('run-a','branch-a','head-a')
  })

  it('links second-season historical shared-ancestor Edition through selected Branch',async()=>{
    context.branch.branch_id='branch-b'
    context.branch.saved_head_revision_id='head-b'
    const f=worldFixture()
    const entities=f.state!.entities as Record<string,unknown>[]
    ;(f.state!.package_versions as Record<string,unknown>[]).push({
      package_id:'calendar-2002-2003',package_type:'Calendar'})
    entities.push(
      {source_package_id:'calendar-2002-2003',source_entity_id:'calendar.metadata',
        entity_kind:'calendar.metadata.v1',payload:{season:'2002/2003'}},
      {source_package_id:'calendar-2002-2003',source_entity_id:'old-event',
        entity_kind:'calendar.event.v1',payload:{event_id:'old-event',
          season:'2002/2003',season_week:8,event_name:'Shared Future Open',
          host_country:'CZE',status:'planned'}}
    )
    api.getSavedRevision.mockResolvedValue({
      ...historicalDetail('rev-shared','Old Czechia','branch-a','branch-b'),
      payload:{run:{run_id:'run-a'},branch:{branch_id:'branch-a'},content:{
        run_package_state:{fingerprint:f.fingerprint,state:f.state}}}
    })
    context.language='cs'
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=tournaments&revision=rev-shared&year=2030&q=old')
    const table=await screen.findByRole('table',{name:'Country tournament editions 2002/2003'})
    const href=within(table).getByRole('link',{name:'Shared Future Open'}).getAttribute('href')!
    const url=new URL(href,'https://test.invalid')
    expect(url.pathname).toBe('/admin/runs/run-a/tour/calendar/old-event')
    expect(url.searchParams.get('branch')).toBe('branch-b')
    expect(url.searchParams.get('revision')).toBe('rev-shared')
    expect(url.searchParams.get('season')).toBe('2')
    expect(url.searchParams.get('fromCountry')).toContain('revision=rev-shared&year=2030&q=old')
    expect(screen.getByLabelText('Country Run-owned tournaments')).toHaveTextContent(
      'neměnnou uloženou edici')
    expect(api.getSavedRevision).toHaveBeenCalledWith('run-a','branch-b','rev-shared')
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })
  it('shows a localized fail-closed error instead of duplicate saved tournament rows',async()=>{
    const f=worldFixture()
    const versions=f.state!.package_versions as Record<string,unknown>[]
    const entities=f.state!.entities as Record<string,unknown>[]
    for(const [packageId,season,host] of [
      ['calendar-first','2000/2001','CZE'],['calendar-second','2001/2002','USA']
    ] as const){
      versions.push({package_id:packageId,package_type:'Calendar'})
      entities.push({source_package_id:packageId,source_entity_id:'calendar.metadata',
        entity_kind:'calendar.metadata.v1',payload:{season}})
      entities.push({source_package_id:packageId,source_entity_id:'same-event',
        entity_kind:'calendar.event.v1',payload:{event_id:'same-event',season,
          season_week:8,event_name:'Ambiguous Open',host_country:host,status:'planned'}})
    }
    api.getSavedRevision.mockResolvedValue({
      ...historicalDetail('head-a','Saved Czechia'),
      payload:{run:{run_id:'run-a'},branch:{branch_id:'branch-a'},content:{
        run_package_state:{fingerprint:f.fingerprint,state:f.state}}}
    })
    context.language='cs'
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=tournaments')
    const panel=await screen.findByLabelText('Country Run-owned tournaments')
    expect(await within(panel).findByRole('alert')).toHaveTextContent(
      'Nejednoznačný uložený kalendář: více balíčků používá stejné ID turnaje: same-event')
    expect(within(panel).queryByRole('table')).not.toBeInTheDocument()
    expect(within(panel).queryByText('Ambiguous Open')).not.toBeInTheDocument()
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


  it('shows canonical Country Records with separate hosted and player nationality results',async()=>{
    api.getRunCountryRecords.mockResolvedValue({
      schema_version:'run_country_records.v1',source:'reachable_saved_revision',
      run_id:'run-a',branch_id:'branch-a',revision_branch_id:'branch-a',
      saved_revision_id:'head-a',country_code:'CZE',calendar_status:'ready',
      published_result_count:2,country_titles:1,country_finalists:1,
      hosted_published_results:1,
      player_results:[{
        event_id:'away',event_name:'Away Championship',season:'2000/2001',
        season_week:3,host_country:'EGY',champion_player_id:'P1',
        champion_name:'Czech Champion',champion_country:'CZE',
        finalist_player_id:'P2',finalist_name:'Egypt Finalist',finalist_country:'EGY',
      }],
      hosted_results:[{
        event_id:'home',event_name:'Prague Open',season:'2000/2001',
        season_week:4,host_country:'CZE',champion_player_id:'P2',
        champion_name:'Egypt Champion',champion_country:'EGY',
        finalist_player_id:'P1',finalist_name:'Czech Finalist',finalist_country:'CZE',
      }]
    })
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=records&year=2020')
    const records=await screen.findByLabelText('Country published records')
    await waitFor(()=>expect(within(records).getByLabelText('Country verified record totals')).toHaveTextContent('1'))
    expect(within(records).getByRole('table',{name:'Country player published results'}))
      .toHaveTextContent('Away Championship')
    expect(within(records).getByRole('table',{name:'Country hosted published results'}))
      .toHaveTextContent('Prague Open')
    expect(api.getRunCountryRecords).toHaveBeenCalledWith('run-a','branch-a','CZE','head-a')
    expect(within(records).getByRole('link',{name:'Czech Champion'})).toHaveAttribute(
      'href','/admin/runs/run-a/people/P1')
  })
  it('filters verified published records by sporting season and reveals tied-holder evidence',async()=>{
    context.time.presentSeason=2
    context.time.presentWeek=1
    api.getRunCountryRecords.mockResolvedValue({
      schema_version:'run_country_records.v1',source:'reachable_saved_revision',
      run_id:'run-a',branch_id:'branch-a',revision_branch_id:'branch-a',
      saved_revision_id:'head-a',country_code:'CZE',calendar_status:'ready',
      published_result_count:3,country_titles:3,country_finalists:0,
      hosted_published_results:3,
      player_results:[
        {event_id:'old',event_name:'Old Open',season:'2000/2001',season_week:4,
          host_country:'CZE',champion_player_id:'P1',champion_name:'Player One',
          champion_country:'CZE',finalist_player_id:'P9',finalist_name:'Foreign',
          finalist_country:'USA'},
        {event_id:'last',event_name:'Last Season',season:'2001/2002',season_week:61,
          host_country:'CZE',champion_player_id:'P2',champion_name:'Player Two',
          champion_country:'CZE',finalist_player_id:'P9',finalist_name:'Foreign',
          finalist_country:'USA'},
        {event_id:'early',event_name:'Early Open',season:'2002/2003',season_week:1,
          host_country:'CZE',champion_player_id:'P1',champion_name:'Player One',
          champion_country:'CZE',finalist_player_id:'P9',finalist_name:'Foreign',
          finalist_country:'USA'},
      ],
      hosted_results:[
        {event_id:'old',event_name:'Old Open',season:'2000/2001',season_week:4,
          host_country:'CZE',champion_player_id:'P1',champion_name:'Player One',
          champion_country:'CZE',finalist_player_id:'P9',finalist_name:'Foreign',
          finalist_country:'USA'},
        {event_id:'last',event_name:'Last Season',season:'2001/2002',season_week:61,
          host_country:'CZE',champion_player_id:'P2',champion_name:'Player Two',
          champion_country:'CZE',finalist_player_id:'P9',finalist_name:'Foreign',
          finalist_country:'USA'},
        {event_id:'early',event_name:'Early Open',season:'2002/2003',season_week:1,
          host_country:'CZE',champion_player_id:'P1',champion_name:'Player One',
          champion_country:'CZE',finalist_player_id:'P9',finalist_name:'Foreign',
          finalist_country:'USA'},
      ]
    })
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=records&year=2050&q=keep')
    const panel=await screen.findByLabelText('Country published records')
    const totals=await within(panel).findByLabelText('Country verified record totals')
    expect(totals).toHaveTextContent('3')
    await userEvent.click(within(panel).getAllByRole('button',{name:'Evidence'})[0])
    const detail=within(panel).getByLabelText('Country record detail')
    expect(detail).toHaveTextContent('Player One')
    expect(detail).toHaveTextContent('2000/2001')
    const href=within(detail).getByRole('link',{name:'Old Open'}).getAttribute('href')!
    const parsed=new URL(href,'https://test.invalid')
    expect(parsed.pathname).toBe('/admin/runs/run-a/tour/calendar/old')
    expect(parsed.searchParams.get('season')).toBe('0')
    expect(parsed.searchParams.get('revision')).toBe('head-a')
    expect(parsed.searchParams.get('fromCountry')).toContain('year=2050&q=keep')
    await userEvent.click(within(detail).getByRole('button',{name:'Close detail'}))
    await userEvent.selectOptions(within(panel).getByRole('combobox',{name:'Country record period'}),'season')
    await userEvent.selectOptions(within(panel).getByRole('combobox',{name:'Country record season'}),'1')
    expect(within(panel).getByRole('table',{name:'Country player published results'}))
      .toHaveTextContent('Last Season')
    expect(within(panel).getByRole('table',{name:'Country player published results'}))
      .not.toHaveTextContent('Old Open')
    expect(within(panel).getByLabelText('Country sporting record interval'))
      .toHaveTextContent('2001/2002 · Week 1')
    expect(api.getRunCountryRecords).toHaveBeenCalledTimes(1)
    expect(panel).toHaveTextContent('independent lifetime scope')
  })
  it('does not label missing simulation position or geography year as verified sport-time scope',async()=>{
    context.time.presentSeason=null
    context.time.presentWeek=null
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=records&year=2020')
    const panel=await screen.findByLabelText('Country published records')
    expect(within(panel).getByRole('alert')).toHaveTextContent('Country data year is not a sporting time')
    expect(within(panel).queryByLabelText('Country verified record totals')).not.toBeInTheDocument()
    expect(api.getRunCountryRecords).not.toHaveBeenCalled()
  })
  it('reads historical Country Records from explicit revision and blocks present profile links',async()=>{
    api.getRunCountryRecords.mockResolvedValue({
      schema_version:'run_country_records.v1',source:'reachable_saved_revision',
      run_id:'run-a',branch_id:'branch-a',revision_branch_id:'branch-a',
      saved_revision_id:'rev-old',country_code:'CZE',calendar_status:'ready',
      published_result_count:1,country_titles:1,country_finalists:0,
      hosted_published_results:0,
      player_results:[{
        event_id:'past',event_name:'Archived Open',season:'2000/2001',
        season_week:1,host_country:'EGY',champion_player_id:'P1',
        champion_name:'Former Champion',champion_country:'CZE',
        finalist_player_id:'P2',finalist_name:'Opponent',finalist_country:'EGY',
      }],hosted_results:[]
    })
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=records&revision=rev-old')
    const records=await screen.findByLabelText('Country published records')
    await waitFor(()=>expect(records).toHaveTextContent('Former Champion'))
    expect(records).toHaveTextContent('Historical revision')
    expect(within(records).queryByRole('link',{name:'Former Champion'})).not.toBeInTheDocument()
    expect(api.getRunCountryRecords).toHaveBeenCalledWith('run-a','branch-a','CZE','rev-old')
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })
  it('fails closed without a Saved HEAD and does not call Country Records API',async()=>{
    context.branch.saved_head_revision_id=''
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=records')
    const records=await screen.findByLabelText('Country published records')
    expect(records).toHaveTextContent('No authoritative Saved Revision')
    expect(api.getRunCountryRecords).not.toHaveBeenCalled()
  })


  it('renders match stats from exact Saved HEAD and server-filters season, completion and outcome',async()=>{
    api.getCountrySavedMatchRecords.mockImplementation(async (_r:string,_b:string,_c:string,
      rev:string,opts:Parameters<typeof savedMatchResult>[1])=>{
      const row=matchRow('filtered',{
        season:opts.seasonIndex===1?'2001/2002':'2000/2001',
        completion:opts.resultKind==='walkover'?'walkover':'played',
        winnerCountry:opts.outcome==='loss'?'EGY':'CZE',
        loserCountry:opts.outcome==='loss'?'CZE':'EGY'
      })
      return savedMatchResult(rev,opts,[row],1)
    })
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=records')
    const panel=await screen.findByLabelText('Country saved match records')
    await waitFor(()=>expect(within(panel).getByRole('table',{name:'Country canonical saved matches'}))
      .toHaveTextContent('Open filtered'))
    expect(panel).toHaveTextContent('18')
    expect(api.getCountrySavedMatchRecords).toHaveBeenCalledWith(
      'run-a','branch-a','CZE','head-a',{
        seasonIndex:null,resultKind:'all',outcome:'all',offset:0,limit:25
      })
    await userEvent.selectOptions(within(panel).getByRole('combobox',{name:'Country match season'}),'1')
    await waitFor(()=>expect(api.getCountrySavedMatchRecords).toHaveBeenCalledWith(
      'run-a','branch-a','CZE','head-a',{
        seasonIndex:1,resultKind:'all',outcome:'all',offset:0,limit:25
      }))
    await userEvent.selectOptions(within(panel).getByRole('combobox',{name:'Country match completion'}),'walkover')
    await userEvent.selectOptions(within(panel).getByRole('combobox',{name:'Country match outcome'}),'loss')
    await waitFor(()=>expect(api.getCountrySavedMatchRecords).toHaveBeenCalledWith(
      'run-a','branch-a','CZE','head-a',{
        seasonIndex:1,resultKind:'walkover',outcome:'loss',offset:0,limit:25
      }))
    await waitFor(()=>expect(within(panel).getByRole('table',{name:'Country canonical saved matches'}))
      .toHaveTextContent('2001/2002'))
    expect(panel).toHaveTextContent('Walkover')
    expect(panel).toHaveTextContent('18')
    expect(within(panel).getByRole('link',{name:'Match filtered'})).toHaveAttribute(
      'href','/admin/runs/run-a/people/winner-filtered/matches/event-filtered/filtered')
  })
  it('paginates matches server-side and resets to first page when a filter changes',async()=>{
    api.getCountrySavedMatchRecords.mockImplementation(async (_r:string,_b:string,_c:string,
      rev:string,opts:Parameters<typeof savedMatchResult>[1])=>{
      const count=opts.outcome==='win'?1:26
      const rows=Array.from({length:Math.max(0,Math.min(opts.limit,count-opts.offset))},(_,i)=>
        matchRow('m'+(opts.offset+i)))
      return savedMatchResult(rev,opts,rows,count)
    })
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=records')
    const panel=await screen.findByLabelText('Country saved match records')
    await waitFor(()=>expect(within(panel).getByRole('table',{name:'Country canonical saved matches'}))
      .toHaveTextContent('Open m0'))
    expect(within(panel).getByLabelText('Country match pagination')).toHaveTextContent('Page 1 / 2')
    await userEvent.click(within(panel).getByRole('button',{name:'Next →'}))
    await waitFor(()=>expect(api.getCountrySavedMatchRecords).toHaveBeenCalledWith(
      'run-a','branch-a','CZE','head-a',{
        seasonIndex:null,resultKind:'all',outcome:'all',offset:25,limit:25
      }))
    await waitFor(()=>expect(within(panel).getByRole('table',{name:'Country canonical saved matches'}))
      .toHaveTextContent('Open m25'))
    await userEvent.selectOptions(within(panel).getByRole('combobox',{name:'Country match outcome'}),'win')
    await waitFor(()=>expect(api.getCountrySavedMatchRecords).toHaveBeenCalledWith(
      'run-a','branch-a','CZE','head-a',{
        seasonIndex:null,resultKind:'all',outcome:'win',offset:0,limit:25
      }))
    await waitFor(()=>expect(within(panel).getByLabelText('Country match pagination'))
      .toHaveTextContent('Page 1 / 1'))
  })
  it('uses historical Saved Revision for matches without present links or current source leaks',async()=>{
    api.getCountrySavedMatchRecords.mockImplementation(async (_r:string,_b:string,_c:string,
      rev:string,opts:Parameters<typeof savedMatchResult>[1])=>
      savedMatchResult(rev,opts,[matchRow('historic')],1))
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=records&revision=rev-old')
    const panel=await screen.findByLabelText('Country saved match records')
    await waitFor(()=>expect(panel).toHaveTextContent('Open historic'))
    expect(api.getCountrySavedMatchRecords).toHaveBeenCalledWith(
      'run-a','branch-a','CZE','rev-old',{
        seasonIndex:null,resultKind:'all',outcome:'all',offset:0,limit:25
      })
    expect(within(panel).queryByRole('link',{name:'Match historic'})).not.toBeInTheDocument()
    expect(within(panel).queryByRole('link',{name:'Winner historic'})).not.toBeInTheDocument()
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })
  it('never requests saved matches without an authoritative Saved Revision',async()=>{
    context.branch.saved_head_revision_id=''
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=records')
    const panel=await screen.findByLabelText('Country saved match records')
    expect(panel).toHaveTextContent('No Saved Revision')
    expect(api.getCountrySavedMatchRecords).not.toHaveBeenCalled()
  })
  it('reports inaccessible match source instead of displaying made-up zeros',async()=>{
    api.getCountrySavedMatchRecords.mockRejectedValue(new Error('409 invalid national identity'))
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=records')
    const panel=await screen.findByLabelText('Country saved match records')
    await waitFor(()=>expect(within(panel).getByRole('alert'))
      .toHaveTextContent('invalid national identity'))
    expect(within(panel).queryByLabelText('Country saved match totals')).not.toBeInTheDocument()
  })


  it('shows real Saved HEAD player standings and a safe current profile link',async()=>{
    api.getCountryPlayerStandings.mockImplementation(async (_r:string,_b:string,_c:string,
      rev:string,offset=0,limit=25)=>savedStandings(rev,offset,limit,[
        standing('P1',1,1),standing('P2',2,0)
      ],2))
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=records')
    const panel=await screen.findByLabelText('Country canonical player standings')
    const table=await within(panel).findByRole('table',{name:'Country player standings table'})
    expect(table).toHaveTextContent('Player P1')
    expect(table).toHaveTextContent('Player P2')
    expect(within(table).getByRole('link',{name:'Player P1'})).toHaveAttribute(
      'href','/admin/runs/run-a/people/P1')
    expect(api.getCountryPlayerStandings).toHaveBeenCalledWith(
      'run-a','branch-a','CZE','head-a',0,25)
    expect(panel).toHaveTextContent('not Official Ranking points')
    expect(within(table).getAllByRole('row')).toHaveLength(3)
  })
  it('paginates country player standings by exact Saved Revision, never first 25 matches',async()=>{
    api.getCountryPlayerStandings.mockImplementation(async (_r:string,_b:string,_c:string,
      rev:string,offset=0,limit=25)=>{
      const rows=Array.from({length:Math.max(0,Math.min(limit,26-offset))},(_,i)=>
        standing('P'+String(offset+i).padStart(2,'0'),offset+i+1))
      return savedStandings(rev,offset,limit,rows,26)
    })
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=records')
    const panel=await screen.findByLabelText('Country canonical player standings')
    await waitFor(()=>expect(within(panel).getByRole('table',{name:'Country player standings table'}))
      .toHaveTextContent('Player P00'))
    expect(within(panel).getByLabelText('Country player standings pagination'))
      .toHaveTextContent('Page 1 / 2')
    await userEvent.click(within(panel).getByRole('button',{name:'Next →'}))
    await waitFor(()=>expect(api.getCountryPlayerStandings).toHaveBeenCalledWith(
      'run-a','branch-a','CZE','head-a',25,25))
    await waitFor(()=>expect(within(panel).getByRole('table',{name:'Country player standings table'}))
      .toHaveTextContent('Player P25'))
    expect(within(panel).getByLabelText('Country player standings pagination'))
      .toHaveTextContent('Page 2 / 2')
  })
  it('uses a historical player standing revision without present profile links',async()=>{
    api.getCountryPlayerStandings.mockImplementation(async (_r:string,_b:string,_c:string,
      rev:string,offset=0,limit=25)=>savedStandings(rev,offset,limit,[standing('P1',1,1)],1))
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=records&revision=rev-old')
    const panel=await screen.findByLabelText('Country canonical player standings')
    await waitFor(()=>expect(within(panel).getByRole('table',{name:'Country player standings table'}))
      .toHaveTextContent('Player P1'))
    expect(api.getCountryPlayerStandings).toHaveBeenCalledWith(
      'run-a','branch-a','CZE','rev-old',0,25)
    expect(within(panel).queryByRole('link',{name:'Player P1'})).not.toBeInTheDocument()
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })
  it('does not request country player standings without a saved revision',async()=>{
    context.branch.saved_head_revision_id=''
    mountWorld('/admin/runs/run-a/world/countries/CZE?tab=records')
    const panel=await screen.findByLabelText('Country canonical player standings')
    expect(panel).toHaveTextContent('No Saved Revision')
    expect(api.getCountryPlayerStandings).not.toHaveBeenCalled()
  })

})
