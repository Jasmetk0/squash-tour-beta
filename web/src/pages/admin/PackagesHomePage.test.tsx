import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom'
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
function mount(path:string, worldJumpTab?:'contents'|'validation'):void {
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>
    <MemoryRouter initialEntries={[path]}><LanguageProvider><LanguageSwitch />{worldJumpTab&&<Link to={'/admin/packages/world/other?tab='+worldJumpTab}>Open another World</Link>}<Routes>
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
    await waitFor(()=>expect(screen.getByRole('link',{name:/Země/})).toHaveTextContent('1 registrovaný'))
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
  it('does not query World packages or show fake loading for categories without a registry',async()=>{
    api.listWorldPackages.mockRejectedValue(new Error('irrelevant World outage'))
    mount('/admin/packages/category/hybrid')
    expect(screen.getByRole('heading',{name:'Hybridní'})).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Z této kategorie zatím nemáme ověřený inventář balíčků.')
    expect(screen.queryByRole('searchbox')).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(api.listWorldPackages).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button',{name:'Switch language'}))
    expect(screen.getByRole('status')).toHaveTextContent('A verified package inventory for this category is not yet available.')
    expect(api.listWorldPackages).not.toHaveBeenCalled()
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
  it('formats population and content totals in the selected language without changing data',async()=>{
    api.getWorldPackageCountries.mockResolvedValue({world_id:'demo',countries:[
      {code:'CZE',name:'Czechia',population:1234567,region:'Europe'}
    ]})
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    expect(screen.getByText(/2 země · 1 kontinent · 1 region/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Obsah'}))
    expect(await screen.findByText(/Europe · 1\s234\s567/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Switch language'}))
    expect(screen.getByText('Europe · 1,234,567')).toBeInTheDocument()
    expect(api.getWorldPackageCountries).toHaveBeenCalledTimes(1)
    await userEvent.click(screen.getByRole('button',{name:'Overview'}))
    expect(screen.getByText(/2 countries · 1 continent · 1 region/)).toBeInTheDocument()
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
  it('finds accented catalog names and clears empty-result filters without refetching',async()=>{
    api.listWorldPackages.mockResolvedValue({packages:[
      {...world,world_id:'czworld',name:'České země'},
      empty
    ]})
    mount('/admin/packages/all')
    expect(await screen.findByText('České země')).toBeInTheDocument()
    const search=screen.getByRole('searchbox',{name:'Hledání'})
    await userEvent.type(search,' CESKE ')
    expect(screen.getByText('České země')).toBeInTheDocument()
    expect(screen.queryByText('Empty World')).not.toBeInTheDocument()
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Package origin'}),'custom')
    expect(screen.getByText(/Žádný evidovaný balíček neodpovídá filtru/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Vymazat filtry'}))
    expect(search).toHaveValue('')
    expect(screen.getByRole('combobox',{name:'Package origin'})).toHaveValue('any')
    expect(screen.getByRole('combobox',{name:'Package status'})).toHaveValue('any')
    expect(screen.getByText('České země')).toBeInTheDocument()
    expect(screen.getByText('Empty World')).toBeInTheDocument()
    expect(api.listWorldPackages).toHaveBeenCalledTimes(1)
  })

  it('distinguishes a filtered-out inventory from a truly empty category',async()=>{
    mount('/admin/packages/all')
    expect(await screen.findByText('Demo World')).toBeInTheDocument()
    await userEvent.type(screen.getByRole('searchbox',{name:'Hledání'}),'not-a-real-package')
    expect(screen.getByText(/Žádný evidovaný balíček/)).toBeInTheDocument()
  })


  it('distinguishes empty World contents and validation rows from load failures',async()=>{
    api.getWorldPackageCountries.mockResolvedValue({world_id:'demo',countries:[]})
    api.getWorldPackageGeography.mockResolvedValue({world_id:'demo',continents:[],regions:[],travel_regions:[],timezone_areas:[]})
    api.getWorldPackageValidation.mockResolvedValue({
      world_id:'demo',status:'valid',error_count:0,warning_count:0,info_count:0,checks:[]
    })
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Obsah'}))
    expect(await screen.findByText('V balíčku nejsou žádné země.')).toBeInTheDocument()
    await userEvent.click(screen.getByText('Kontinenty (0)'))
    expect(screen.getAllByText('V této části nejsou žádné položky.')).toHaveLength(4)
    await userEvent.click(screen.getByRole('button',{name:'Kontrola'}))
    expect(await screen.findByText('Kontrola nevrátila žádné jednotlivé záznamy.')).toBeInTheDocument()
    expect(screen.getByText(/platné · 0 chyb · 0 varování/)).toBeInTheDocument()
  })
  it('resets local country search and ordering when router reuses the detail for another World',async()=>{
    api.getWorldPackage.mockImplementation(async(id:string)=>id==='demo'?world:{...world,world_id:'other',name:'Other World'})
    api.getWorldPackageCountries.mockImplementation(async(id:string)=>({world_id:id,countries:[
      {code:'CZE',name:'Czechia',population:100,region:'Europe'},
      {code:'USA',name:'United States',population:200,region:'America'}
    ]}))
    api.getWorldPackageGeography.mockImplementation(async(id:string)=>({world_id:id,continents:[],regions:[],travel_regions:[],timezone_areas:[]}))
    mount('/admin/packages/world/demo?tab=contents','contents')
    expect(await screen.findByRole('link',{name:'Czechia (CZE)'})).toBeInTheDocument()
    const search=screen.getByRole('searchbox',{name:'Hledat zemi, kód nebo region'})
    await userEvent.type(search,'cesko-nonexistent')
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Package country sort'}),'population')
    expect(screen.getByText('Žádná země neodpovídá hledání.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link',{name:'Open another World'}))
    expect(await screen.findByRole('heading',{name:'Other World'})).toBeInTheDocument()
    await waitFor(()=>expect(screen.getByRole('searchbox',{name:'Hledat zemi, kód nebo region'})).toHaveValue(''))
    expect(screen.getByRole('combobox',{name:'Package country sort'})).toHaveValue('source')
    expect(await screen.findByRole('link',{name:'Czechia (CZE)'})).toBeInTheDocument()
    expect(api.getWorldPackageCountries).toHaveBeenCalledTimes(2)
  })

  it('searches country names, codes and regions without accents or inventory writes',async()=>{
    api.getWorldPackageCountries.mockResolvedValue({world_id:'demo',countries:[
      {code:'CZE',name:'Česko',region:'Střední Evropa',population:100},
      {code:'USA',name:'United States',region:'America',population:200}
    ]})
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Obsah'}))
    expect(await screen.findByRole('link',{name:'Česko (CZE)'})).toBeInTheDocument()
    const search=screen.getByRole('searchbox',{name:'Hledat zemi, kód nebo region'})
    await userEvent.type(search,'cesko')
    expect(screen.getByRole('link',{name:'Česko (CZE)'})).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'United States (USA)'})).not.toBeInTheDocument()
    await userEvent.clear(search)
    await userEvent.type(search,' stredni ')
    expect(screen.getByText(/Zobrazeno 1 z 2 zemí/)).toBeInTheDocument()
    expect(screen.getByRole('link',{name:'Česko (CZE)'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Switch language'}))
    expect(screen.getByRole('searchbox',{name:'Search countries, codes or regions'})).toHaveValue(' stredni ')
    expect(screen.getByRole('link',{name:'Česko (CZE)'})).toBeInTheDocument()
    const englishSearch=screen.getByRole('searchbox',{name:'Search countries, codes or regions'})
    await userEvent.clear(englishSearch)
    await userEvent.type(englishSearch,'not-an-existing-country')
    expect(screen.getByText('No country matches the search.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Clear country search'}))
    expect(englishSearch).toHaveValue('')
    expect(screen.getByRole('link',{name:'United States (USA)'})).toBeInTheDocument()
    expect(api.getWorldPackageCountries).toHaveBeenCalledTimes(1)
  })

  it('sorts filtered countries by localized name or population without modifying API inventory',async()=>{
    api.getWorldPackageCountries.mockResolvedValue({world_id:'demo',countries:[
      {code:'USA',name:'United States',region:'North America',population:200},
      {code:'CZE',name:'Česko',region:'Europe',population:100},
      {code:'BWA',name:'Botswana',region:'Africa',population:300}
    ]})
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Obsah'}))
    expect(await screen.findByRole('link',{name:'Česko (CZE)'})).toBeInTheDocument()
    const countries=screen.getByRole('list',{name:'World package countries'})
    const names=()=>within(countries).getAllByRole('link').map(x=>x.textContent)
    expect(names()).toEqual(['United States (USA)','Česko (CZE)','Botswana (BWA)'])
    const sorter=screen.getByRole('combobox',{name:'Package country sort'})
    await userEvent.selectOptions(sorter,'name')
    expect(names()).toEqual(['Botswana (BWA)','Česko (CZE)','United States (USA)'])
    await userEvent.selectOptions(sorter,'population')
    expect(names()).toEqual(['Botswana (BWA)','United States (USA)','Česko (CZE)'])
    await userEvent.click(screen.getByRole('button',{name:'Switch language'}))
    expect(sorter).toHaveValue('population')
    expect(names()).toEqual(['Botswana (BWA)','United States (USA)','Česko (CZE)'])
    expect(api.getWorldPackageCountries).toHaveBeenCalledTimes(1)
  })

  it('does not retain validation severity filters after navigating to another World',async()=>{
    api.getWorldPackage.mockImplementation(async(id:string)=>id==='demo'?world:{...world,world_id:'other',name:'Other World'})
    api.getWorldPackageCountries.mockImplementation(async(id:string)=>({world_id:id,countries:[]}))
    api.getWorldPackageValidation.mockImplementation(async(id:string)=>({world_id:id,status:'warnings',error_count:0,warning_count:1,info_count:0,checks:[
      {code:'review',severity:'warning',status:'warning',message:id+' warning',path:null,field:null}
    ]}))
    mount('/admin/packages/world/demo?tab=validation','validation')
    expect(await screen.findByText('demo warning')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Package validation severity filter'}),'error')
    const checkSearch=screen.getByRole('searchbox',{name:'Package validation search'})
    await userEvent.type(checkSearch,'old-world')
    expect(screen.getByText('Zvolenému filtru neodpovídají žádné záznamy kontroly.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link',{name:'Open another World'}))
    expect(await screen.findByRole('heading',{name:'Other World'})).toBeInTheDocument()
    await waitFor(()=>expect(screen.getByRole('combobox',{name:'Package validation severity filter'})).toHaveValue('all'))
    expect(screen.getByRole('searchbox',{name:'Package validation search'})).toHaveValue('')
    expect(await screen.findByText('other warning')).toBeInTheDocument()
    expect(api.getWorldPackageValidation).toHaveBeenCalledTimes(2)
  })

  it('filters validation severity without changing original counts or diagnostic messages',async()=>{
    api.getWorldPackageValidation.mockResolvedValue({world_id:'demo',status:'errors',error_count:1,warning_count:1,info_count:1,checks:[
      {code:'broken_country',severity:'error',status:'failed',message:'Country is invalid',path:'countries/CZE/data.json',field:'name'},
      {code:'country_warning',severity:'warning',status:'warning',message:'Country detail to inspect',path:'countries/CZE/config.json',field:'squash_access'},
      {code:'source_info',severity:'info',status:'passed',message:'Imported as supplied',path:null,field:null}
    ]})
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Kontrola'}))
    expect(await screen.findByText('Country is invalid')).toBeInTheDocument()
    expect(screen.getByText(/1 chyba · 1 varování · 1 informace/)).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Package validation severity filter'}),'error')
    expect(screen.getByText('Country is invalid')).toBeInTheDocument()
    expect(screen.getByText('Výsledek kontroly: nesplněno (failed)')).toBeInTheDocument()
    expect(screen.queryByText('Country detail to inspect')).not.toBeInTheDocument()
    expect(screen.getByText(/Zobrazeno 1 z 3 kontrol/)).toBeInTheDocument()
    expect(screen.getByText(/1 chyba · 1 varování · 1 informace/)).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Package validation severity filter'}),'info')
    expect(screen.getByText('Imported as supplied')).toBeInTheDocument()
    expect(screen.getByText('Výsledek kontroly: splněno (passed)')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Switch language'}))
    expect(screen.getByRole('combobox',{name:'Package validation severity filter'})).toHaveValue('info')
    expect(screen.getByText('Imported as supplied')).toBeInTheDocument()
    expect(screen.getByText('Check outcome: passed')).toBeInTheDocument()
    expect(api.getWorldPackageValidation).toHaveBeenCalledTimes(1)
  })

  it('searches validation code, message, path and field without refetching or changing totals',async()=>{
    api.getWorldPackageValidation.mockResolvedValue({world_id:'demo',status:'errors',error_count:1,warning_count:1,info_count:1,checks:[
      {code:'country_error',severity:'error',status:'failed',message:'Chybí název země',path:'countries/CZE/název.json',field:'display_name'},
      {code:'population_warning',severity:'warning',status:'warning',message:'Population incomplete',path:'countries/USA/population.json',field:'population_by_year'},
      {code:'source_info',severity:'info',status:'passed',message:'Source verified',path:null,field:null}
    ]})
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Kontrola'}))
    expect(await screen.findByText('Chybí název země')).toBeInTheDocument()
    const search=screen.getByRole('searchbox',{name:'Package validation search'})
    await userEvent.type(search,' NAZEV ')
    expect(screen.getByText('Chybí název země')).toBeInTheDocument()
    expect(screen.queryByText('Population incomplete')).not.toBeInTheDocument()
    expect(screen.getByText(/Zobrazeno 1 z 3 kontrol/)).toBeInTheDocument()
    expect(screen.getByText(/1 chyba · 1 varování · 1 informace/)).toBeInTheDocument()
    await userEvent.clear(search)
    await userEvent.type(search,'population_by_year')
    expect(screen.getByText('Population incomplete')).toBeInTheDocument()
    await userEvent.clear(search)
    await userEvent.type(search,'country_error')
    expect(screen.getByText('Chybí název země')).toBeInTheDocument()
    await userEvent.clear(search)
    await userEvent.type(search,'CZE/nazev.json')
    expect(screen.getByText('Chybí název země')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Switch language'}))
    expect(search).toHaveValue('CZE/nazev.json')
    expect(screen.getByText('Chybí název země')).toBeInTheDocument()
    expect(api.getWorldPackageValidation).toHaveBeenCalledTimes(1)
  })

  it('composes validation search with severity and clears both filters on no results',async()=>{
    api.getWorldPackageValidation.mockResolvedValue({world_id:'demo',status:'errors',error_count:1,warning_count:1,info_count:0,checks:[
      {code:'missing',severity:'error',status:'failed',message:'Missing country',path:'countries/CZE',field:null},
      {code:'warn',severity:'warning',status:'warning',message:'Population warning',path:'countries/USA',field:null}
    ]})
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Kontrola'}))
    expect(await screen.findByText('Missing country')).toBeInTheDocument()
    const search=screen.getByRole('searchbox',{name:'Package validation search'})
    await userEvent.type(search,'Population')
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Package validation severity filter'}),'error')
    expect(screen.getByText('Zvolenému filtru neodpovídají žádné záznamy kontroly.')).toBeInTheDocument()
    expect(screen.queryByText('Population warning')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Zobrazit všechny kontroly'}))
    expect(search).toHaveValue('')
    expect(screen.getByRole('combobox',{name:'Package validation severity filter'})).toHaveValue('all')
    expect(screen.getByText('Missing country')).toBeInTheDocument()
    expect(screen.getByText('Population warning')).toBeInTheDocument()
    expect(api.getWorldPackageValidation).toHaveBeenCalledTimes(1)
  })

  it('reports a failed World-country query instead of claiming no countries',async()=>{
    api.getWorldPackageCountries.mockRejectedValue(new Error('country service offline'))
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Obsah'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('country service offline')
    expect(screen.queryByText('V balíčku nejsou žádné země.')).not.toBeInTheDocument()
  })

  it('distinguishes zero matching checks from an empty validation response',async()=>{
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Kontrola'}))
    expect(await screen.findByText('Country detail to inspect')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByRole('combobox',{name:'Package validation severity filter'}),'error')
    expect(screen.getByText('Zvolenému filtru neodpovídají žádné záznamy kontroly.')).toBeInTheDocument()
    expect(screen.queryByText('Kontrola nevrátila žádné jednotlivé záznamy.')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Zobrazit všechny kontroly'}))
    expect(screen.getByRole('combobox',{name:'Package validation severity filter'})).toHaveValue('all')
    expect(screen.getByText('Country detail to inspect')).toBeInTheDocument()
    expect(api.getWorldPackageValidation).toHaveBeenCalledTimes(1)
  })

  it('rejects a detail response from another World instead of showing foreign metadata',async()=>{
    api.getWorldPackage.mockResolvedValueOnce({...world,world_id:'other',name:'Wrong World'})
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('alert')).toHaveTextContent('požadováno demo, vráceno other')
    expect(screen.queryByRole('heading',{name:'Wrong World'})).not.toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Obsah'})).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Znovu načíst detail balíčku'}))
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    expect(api.getWorldPackage).toHaveBeenCalledTimes(2)
  })

  it('retries a failed package detail request without navigating away',async()=>{
    api.getWorldPackage.mockRejectedValueOnce(new Error('detail temporarily offline'))
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('alert')).toHaveTextContent('detail temporarily offline')
    await userEvent.click(screen.getByRole('button',{name:'Znovu načíst detail balíčku'}))
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    expect(api.getWorldPackage).toHaveBeenCalledTimes(2)
  })
  it('rejects foreign country and geography data with independent recovery',async()=>{
    api.getWorldPackageCountries.mockResolvedValueOnce({world_id:'other',countries:[{code:'OTH',name:'Foreign Country',population:1,region:'Other'}]})
    api.getWorldPackageGeography.mockResolvedValueOnce({world_id:'other',continents:[{code:'XX',name:'Foreign Continent'}],regions:[],travel_regions:[],timezone_areas:[]})
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Obsah'}))
    await waitFor(()=>expect(screen.getAllByRole('alert')).toHaveLength(2))
    expect(screen.queryByText('Foreign Country (OTH)')).not.toBeInTheDocument()
    expect(screen.queryByText('Foreign Continent')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Znovu načíst země'}))
    expect(await screen.findByRole('link',{name:'Czechia (CZE)'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Znovu načíst geografii'}))
    expect(await screen.findByText('Kontinenty (1)')).toBeInTheDocument()
    expect(api.getWorldPackageCountries).toHaveBeenCalledTimes(2)
    expect(api.getWorldPackageGeography).toHaveBeenCalledTimes(2)
  })

  it('rejects mismatched validation results without showing foreign checks',async()=>{
    api.getWorldPackageValidation.mockResolvedValueOnce({world_id:'other',status:'valid',error_count:0,warning_count:0,info_count:0,checks:[{code:'foreign',severity:'info',status:'passed',message:'Foreign check',path:null,field:null}]})
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Kontrola'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('požadováno demo, vráceno other')
    expect(screen.queryByText('Foreign check')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Znovu načíst kontrolu'}))
    expect(await screen.findByText('Country detail to inspect')).toBeInTheDocument()
    expect(api.getWorldPackageValidation).toHaveBeenCalledTimes(2)
  })

  it('does not create links from a foreign country response on the validation tab',async()=>{
    api.getWorldPackageCountries.mockResolvedValueOnce({world_id:'other',countries:[
      {code:'CZE',name:'Impostor',population:10,region:'Fake'}
    ]})
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Kontrola'}))
    expect(await screen.findByText('Country detail to inspect')).toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent('požadováno demo, vráceno other')
    expect(screen.queryByRole('link',{name:/Otevřít dotčenou zemi/})).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Znovu načíst země'}))
    expect(await screen.findByRole('link',{name:/Otevřít dotčenou zemi/})).toHaveAttribute('href','/admin/world/library/demo/countries/CZE')
    expect(api.getWorldPackageCountries).toHaveBeenCalledTimes(2)
    expect(api.getWorldPackageValidation).toHaveBeenCalledTimes(1)
  })

  it('can reload failed geography and validation separately without changing the active source',async()=>{
    api.getWorldPackageGeography.mockRejectedValueOnce(new Error('geography offline'))
    api.getWorldPackageValidation.mockRejectedValueOnce(new Error('validation offline'))
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Obsah'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('geography offline')
    await userEvent.click(screen.getByRole('button',{name:'Znovu načíst geografii'}))
    expect(await screen.findByText('Kontinenty (1)')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Kontrola'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('validation offline')
    await userEvent.click(screen.getByRole('button',{name:'Znovu načíst kontrolu'}))
    expect(await screen.findByText('Country detail to inspect')).toBeInTheDocument()
    expect(api.getWorldPackageGeography).toHaveBeenCalledTimes(2)
    expect(api.getWorldPackageValidation).toHaveBeenCalledTimes(2)
    expect(api.getWorldPackage).toHaveBeenCalledTimes(1)
  })

  it('recovers an unavailable World registry through a read-only retry in both languages',async()=>{
    api.listWorldPackages.mockRejectedValueOnce(new Error('temporary outage'))
      .mockResolvedValue({packages:[world]})
    mount('/admin/packages/all')
    expect(await screen.findByRole('alert')).toHaveTextContent('temporary outage')
    expect(screen.queryByText('Demo World')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Switch language'}))
    await userEvent.click(screen.getByRole('button',{name:'Retry package catalog'}))
    expect(await screen.findByText('Demo World')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(api.listWorldPackages).toHaveBeenCalledTimes(2)
    expect(api.getWorldPackage).not.toHaveBeenCalled()
  })
  it('recovers validation country links independently without rerunning validation',async()=>{
    api.getWorldPackageCountries.mockRejectedValueOnce(new Error('country lookup offline'))
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Kontrola'}))
    expect(await screen.findByText('Country detail to inspect')).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:/Otevřít dotčenou zemi/})).not.toBeInTheDocument()
    expect(await screen.findByText(/Odkazy na jednotlivé země nejsou dostupné/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Znovu načíst země'}))
    expect(await screen.findByRole('link',{name:/Otevřít dotčenou zemi/})).toHaveAttribute('href','/admin/world/library/demo/countries/CZE')
    expect(api.getWorldPackageCountries).toHaveBeenCalledTimes(2)
    expect(api.getWorldPackageValidation).toHaveBeenCalledTimes(1)
  })

  it('retries failed country inventory without substituting an empty list',async()=>{
    api.getWorldPackageCountries.mockRejectedValueOnce(new Error('temporary country outage'))
    mount('/admin/packages/world/demo')
    expect(await screen.findByRole('heading',{name:'Demo World'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Obsah'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('temporary country outage')
    expect(screen.queryByText('V balíčku nejsou žádné země.')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Znovu načíst země'}))
    expect(await screen.findByRole('link',{name:'Czechia (CZE)'})).toBeInTheDocument()
    expect(api.getWorldPackageCountries).toHaveBeenCalledTimes(2)
  })

  it('does not substitute fabricated empty inventory on source API failure',async()=>{
    api.listWorldPackages.mockRejectedValue(new Error('registry offline'))
    mount('/admin/packages/all')
    expect(await screen.findByRole('alert')).toHaveTextContent('registry offline')
    expect(screen.queryByText('0 / 0')).not.toBeInTheDocument()
  })
})
