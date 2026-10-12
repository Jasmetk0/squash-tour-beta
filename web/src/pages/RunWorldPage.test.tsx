import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RunWorldPage } from './RunWorldPage'
import { worldFixture } from './runWorldFixture'

const api=vi.hoisted(()=>({getRunPackageState:vi.fn()}))
const context=vi.hoisted(()=>({
  branch:{run_id:'run-a',branch_id:'branch-a',display_name:'Timeline 1'},
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

describe('Run-owned World overview navigation',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    context.branch.run_id='run-a'
    context.time.mode='present'
    context.language='en'
    api.getRunPackageState.mockResolvedValue(worldFixture())
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
    expect(years).not.toHaveTextContent('2010')
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
    expect(screen.getByText('source-v2')).toBeInTheDocument()
    expect(screen.getByText('source-v2#row1')).toBeInTheDocument()
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
