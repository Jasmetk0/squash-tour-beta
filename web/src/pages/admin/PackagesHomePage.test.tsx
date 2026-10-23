import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider, useLanguage } from '../../i18n/LanguageContext'
import { PackagesHomePage, PackagesListPage, PackageWorldDetailPage } from './PackagesHomePage'

const api=vi.hoisted(()=>({
  listWorldPackages:vi.fn(),getWorldPackage:vi.fn(),getWorldPackageCountries:vi.fn(),
  getWorldPackageGeography:vi.fn(),getWorldPackageValidation:vi.fn(),
  ApiError: class ApiError extends Error { status = 500 }
}))
vi.mock('../../api/client',()=>api)
const world={
  world_id:'demo',name:'Demo World',description:'Actual source',type:'official',
  status:'active',source:'built_in',editable:false,version:'v1',fingerprint:'hash-demo',
  country_count:2,continent_count:1,region_count:1,travel_region_count:1,
  timezone_area_count:1,used_by_run_count:null
}
const empty={...world,world_id:'empty',name:'Empty World',country_count:0}
function LanguageSwitch():JSX.Element {
  const {language,setLanguage}=useLanguage()
  return <button type="button" onClick={()=>setLanguage(language==='cs'?'en':'cs')}>Switch language</button>
}
function mount(path:string):void {
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>
    <MemoryRouter initialEntries={[path]}><LanguageProvider><LanguageSwitch /><Routes>
      <Route path="/admin/packages" element={<PackagesHomePage/>}/>
      <Route path="/admin/packages/all" element={<PackagesListPage/>}/>
      <Route path="/admin/packages/category/:categoryId" element={<PackagesListPage/>}/>
      <Route path="/admin/packages/world/:worldId" element={<PackageWorldDetailPage/>}/>
    </Routes></LanguageProvider></MemoryRouter>
  </QueryClientProvider>)
}
describe('source-backed Packages frontend',()=>{
  beforeEach(()=>{
    localStorage.clear();vi.clearAllMocks()
    api.listWorldPackages.mockResolvedValue({packages:[world,world,empty]})
    api.getWorldPackage.mockResolvedValue(world)
    api.getWorldPackageCountries.mockResolvedValue({world_id:'demo',countries:[
      {code:'CZE',name:'Czechia',population:100,region:'Europe'},
      {code:'USA',name:'United States',population:200,region:'America'}
    ]})
    api.getWorldPackageGeography.mockResolvedValue({world_id:'demo',continents:[{code:'EU',name:'Europe'}],regions:[{code:'CENT',name:'Central'}],travel_regions:[{code:'TR',name:'Travel'}],timezone_areas:[{code:'UTC',name:'UTC'}]})
    api.getWorldPackageValidation.mockResolvedValue({world_id:'demo',status:'warnings',error_count:0,warning_count:1,info_count:0,checks:[
      {code:'country_warning',severity:'warning',status:'warning',message:'Country detail to inspect',path:'countries/CZE/config.json',field:'squash_access'}
    ]})
  })
  it('uses a category hub rather than opening a combined list by default',async()=>{
    mount('/admin/packages')
    expect(await screen.findByRole('heading',{name:'Balíčky'})).toBeInTheDocument()
    expect(screen.getByRole('link',{name:/Všechny balíčky/})).toHaveAttribute('href','/admin/packages/all')
    expect(screen.getByRole('link',{name:/Hybridní/})).toHaveAttribute('href','/admin/packages/category/hybrid')
    await waitFor(()=>expect(screen.getByRole('link',{name:/Země/})).toHaveTextContent('1 registrovaných'))
    expect(screen.queryByText('Demo World')).not.toBeInTheDocument()
  })
  it('deduplicates All, searches and filters World packages without fake hybrid sources',async()=>{
    mount('/admin/packages/all')
    expect(await screen.findByText('Demo World')).toBeInTheDocument()
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    await userEvent.type(screen.getByRole('searchbox',{name:'Hledání'}),'empty')
    expect(screen.queryByText('Demo World')).not.toBeInTheDocument()
    expect(screen.getByText('Empty World')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Package origin'}),'custom')
    expect(screen.getByText(/Žádný evidovaný balíček/)).toBeInTheDocument()
  })
  it('does not list Country-less World packages under Countries or any hybrid',async()=>{
    mount('/admin/packages/category/countries')
    expect(await screen.findByText('Demo World')).toBeInTheDocument()
    expect(screen.queryByText('Empty World')).not.toBeInTheDocument()
  })
  it('shows actual content records, linked items and real validation, with no fake apply action',async()=>{
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    expect(screen.getByText('hash-demo')).toBeInTheDocument()
    expect(screen.getByRole('link',{name:'Vytvořit vlastní kopii →'})).toHaveAttribute('href','/admin/world/library/demo')
    await userEvent.click(screen.getByRole('button',{name:'Obsah'}))
    expect(await screen.findByRole('link',{name:'Czechia (CZE)'})).toHaveAttribute('href','/admin/world/library/demo/countries/CZE')
    expect(screen.getByText('Kontinenty (1)')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Kontrola'}))
    expect(await screen.findByText('Country detail to inspect')).toBeInTheDocument()
    expect(screen.getByRole('link',{name:/Otevřít dotčenou zemi/})).toHaveAttribute('href','/admin/world/library/demo/countries/CZE')
    expect(api.getWorldPackageValidation).toHaveBeenCalledWith('demo')
  })
  it('switches languages without changing a filtered catalog or making write requests',async()=>{
    mount('/admin/packages/all')
    expect(await screen.findByText('Demo World')).toBeInTheDocument()
    await userEvent.type(screen.getByRole('searchbox',{name:'Hledání'}),'demo')
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Package status'}),'active')
    await userEvent.click(screen.getByRole('button',{name:'Switch language'}))
    expect(screen.getByRole('searchbox',{name:'Search'})).toHaveValue('demo')
    expect(screen.getByRole('combobox',{name:'Package status'})).toHaveValue('active')
    expect(screen.getByText('Demo World')).toBeInTheDocument()
    expect(screen.queryByText('Empty World')).not.toBeInTheDocument()
    expect(api.getWorldPackage).not.toHaveBeenCalled()
    expect(api.listWorldPackages).toHaveBeenCalledTimes(1)
  })
  it('distinguishes a filtered-out inventory from a truly empty category',async()=>{
    mount('/admin/packages/all')
    expect(await screen.findByText('Demo World')).toBeInTheDocument()
    await userEvent.type(screen.getByRole('searchbox',{name:'Hledání'}),'not-a-real-package')
    expect(screen.getByText(/Žádný evidovaný balíček/)).toBeInTheDocument()
  })

  it('does not substitute fabricated empty inventory on source API failure',async()=>{
    api.listWorldPackages.mockRejectedValue(new Error('registry offline'))
    mount('/admin/packages/all')
    expect(await screen.findByRole('alert')).toHaveTextContent('registry offline')
    expect(screen.queryByText('0 / 0')).not.toBeInTheDocument()
  })
})
