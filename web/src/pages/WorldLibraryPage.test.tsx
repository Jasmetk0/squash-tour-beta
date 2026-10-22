import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { WorldLibraryDetailPage, WorldPackageCountryCreatePage } from './WorldLibraryPage'

const api = vi.hoisted(() => ({ getWorldPackage: vi.fn(), getWorldPackageGeography: vi.fn(), getWorldPackageValidation: vi.fn(), createWorldPackageCountry: vi.fn(), cloneWorldPackage: vi.fn() }))
vi.mock('../i18n/LanguageContext', () => ({ useLanguage: () => ({ language: 'en' }) }))
vi.mock('../api/client', async importOriginal => ({ ...(await importOriginal<object>()), ...api }))

describe('new-scale country creation', () => {
  it('authors explicit tenths on 1–10 without a court-count input', async () => {
    api.getWorldPackage.mockResolvedValue({ type: 'custom', source: 'custom_config', editable: true, fingerprint: 'source-head', world_id: 'custom' })
    api.getWorldPackageGeography.mockResolvedValue({ regions: [{ code: 'EUR', name: 'Europe' }], travel_regions: [], timezone_areas: [], world_id: 'custom' })
    api.createWorldPackageCountry.mockResolvedValue({ country_detail: { package: { world_id: 'custom' }, country: { code: 'AAA' } } })
    const router = createMemoryRouter([
      {path:'/world/:worldId/new',element:<WorldPackageCountryCreatePage />},
      {path:'*',element:<p>Created</p>}
    ],{initialEntries:['/world/custom/new']})
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <RouterProvider router={router} />
    </QueryClientProvider>)
    const popularity = await screen.findByLabelText('squash popularity')
    expect(popularity).toHaveAttribute('min', '1')
    expect(popularity).toHaveAttribute('max', '10')
    expect(popularity).toHaveAttribute('step', '0.1')
    expect(screen.queryByLabelText(/court count/i)).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Code'), { target: { value: 'AAA' } })
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Synthetic country' } })
    fireEvent.change(screen.getByLabelText('Region'), { target: { value: 'EUR' } })
    fireEvent.change(screen.getByLabelText('Population value 2020'), { target: { value: '1000000' } })
    fireEvent.change(popularity, { target: { value: '7.4' } })
    fireEvent.submit(screen.getByRole('button', { name: /Review before saving/i }).closest('form')!)
    expect(api.createWorldPackageCountry).not.toHaveBeenCalled()
    expect(await screen.findByText('Review new country')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm and save' }))
    await waitFor(() => expect(api.createWorldPackageCountry).toHaveBeenCalledWith('custom', expect.objectContaining({
      rating_scale: 'country_ratings_1_10.v2', squash_popularity: 7.4, court_count: null,
    })))
    expect(await screen.findByText('Created')).toBeInTheDocument()
  })
})

describe('late new-country create response', () => {
  it('does not redirect from a different page after the user discards the pending edit', async () => {
    api.getWorldPackage.mockResolvedValue({type:'custom',source:'custom_config',editable:true,
      fingerprint:'create-base',world_id:'custom'})
    api.getWorldPackageGeography.mockResolvedValue({world_id:'custom',
      regions:[{code:'EUR',name:'Europe'}],travel_regions:[],timezone_areas:[]})
    let finish!: (response: unknown) => void
    api.createWorldPackageCountry.mockImplementation(() => new Promise(resolve => {finish = resolve}))
    const router = createMemoryRouter([
      {path:'/world/:worldId/new',element:<WorldPackageCountryCreatePage />},
      {path:'*',element:<p>Other page</p>}
    ],{initialEntries:['/world/custom/new']})
    render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}})}>
      <RouterProvider router={router} />
    </QueryClientProvider>)
    fireEvent.change(await screen.findByLabelText('Code'),{target:{value:'AAA'}})
    fireEvent.change(screen.getByLabelText('Name'),{target:{value:'Test Country'}})
    fireEvent.change(screen.getByLabelText('Region'),{target:{value:'EUR'}})
    fireEvent.change(screen.getByLabelText('Population value 2020'),{target:{value:'100'}})
    fireEvent.click(screen.getByRole('button',{name:'Review before saving'}))
    fireEvent.click(screen.getByRole('button',{name:'Confirm and save'}))
    await waitFor(() => expect(api.createWorldPackageCountry).toHaveBeenCalledWith('custom',
      expect.objectContaining({code:'AAA',expected_package_fingerprint:'create-base'})))
    fireEvent.click(screen.getByRole('link',{name:'Back to countries'}))
    expect(await screen.findByRole('alertdialog',{name:'Unsaved World Package changes'})).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Discard and leave'}))
    expect(await screen.findByText('Other page')).toBeInTheDocument()
    const expectedPath = router.state.location.pathname
    expect(expectedPath).toBe('/admin/world/library/custom/countries')
    await act(async () => {finish({country_detail:{package:{world_id:'custom'},country:{code:'AAA'}}})})
    expect(router.state.location.pathname).toBe(expectedPath)
    expect(screen.getByText('Other page')).toBeInTheDocument()
  })
})

describe('built-in World cloning', () => {
  it('clones the built-in package currently being inspected, not a hard-coded FAX source', async () => {
    api.getWorldPackage.mockResolvedValue({
      world_id: 'real_world',
      name: 'Real World',
      description: 'Earth geography',
      type: 'official',
      status: 'active',
      source: 'built_in',
      editable: false,
      deletable: false,
      archivable: false,
      version: 'v1',
      fingerprint: 'real-world-head',
      country_count: 250,
      continent_count: 7,
      region_count: 10,
      travel_region_count: 10,
      timezone_area_count: 0,
      used_by_run_count: null,
      validation_status: 'valid'
    })
    api.getWorldPackageGeography.mockResolvedValue({
      world_id: 'real_world',
      continents: [],
      regions: [],
      travel_regions: [],
      timezone_areas: [],
      timezone_areas_authored: false
    })
    api.getWorldPackageValidation.mockResolvedValue({
      world_id: 'real_world',
      status: 'valid',
      error_count: 0,
      warning_count: 0,
      info_count: 0,
      checks: []
    })
    api.cloneWorldPackage.mockResolvedValue({
      ok: true,
      dry_run: false,
      source_world_id: 'real_world',
      new_world_id: 'editable_earth',
      target_path: 'config/world_packages/custom/editable_earth',
      created_files: [],
      package: null,
      validation: null,
      errors: []
    })

    const router = createMemoryRouter([
      {path:'/world/:worldId',element:<WorldLibraryDetailPage />}
    ],{initialEntries:['/world/real_world']})
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <RouterProvider router={router} />
    </QueryClientProvider>)

    expect(await screen.findByText('Clone Built-in World')).toBeInTheDocument()
    fireEvent.change(screen.getByPlaceholderText('my_custom_world'), { target: { value: '_bad_id' } })
    fireEvent.change(screen.getByPlaceholderText('My Custom World'), { target: { value: 'Editable Earth' } })
    fireEvent.click(screen.getByRole('button', { name: 'Review custom copy' }))
    expect(screen.getByText(/must start with a lowercase letter or digit/)).toBeInTheDocument()
    expect(api.cloneWorldPackage).not.toHaveBeenCalled()
    fireEvent.change(screen.getByPlaceholderText('my_custom_world'), { target: { value: 'editable_earth' } })
    fireEvent.click(screen.getByRole('button', { name: 'Review custom copy' }))
    expect(screen.getByText('real-world-head')).toBeInTheDocument()
    expect(api.cloneWorldPackage).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm custom copy' }))

    await waitFor(() => expect(api.cloneWorldPackage).toHaveBeenCalledWith(
      'real_world',
      expect.objectContaining({ new_world_id: 'editable_earth', name: 'Editable Earth', dry_run: false })
    ))
  })
})


  it('never confirms a clone with a changed source fingerprint', async () => {
    const pkg = {world_id:'real_world',name:'Real World',description:'Earth',type:'official',
      source:'built_in',editable:false,status:'active',deletable:false,archivable:false,
      version:'v1',fingerprint:'before',country_count:2,continent_count:1,region_count:1,
      travel_region_count:1,timezone_area_count:0,used_by_run_count:null,validation_status:'valid'}
    api.getWorldPackage.mockResolvedValue(pkg)
    api.getWorldPackageGeography.mockResolvedValue({
      world_id:'real_world',continents:[],regions:[],travel_regions:[],
      timezone_areas:[],timezone_areas_authored:false
    })
    api.getWorldPackageValidation.mockResolvedValue({
      world_id:'real_world',status:'valid',error_count:0,warning_count:0,info_count:0,checks:[]
    })
    const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
    const router=createMemoryRouter([{path:'/world/:worldId',element:<WorldLibraryDetailPage />}],
      {initialEntries:['/world/real_world']})
    render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>)
    fireEvent.change(await screen.findByPlaceholderText('my_custom_world'),{target:{value:'custom_copy'}})
    fireEvent.change(screen.getByPlaceholderText('My Custom World'),{target:{value:'Edited World'}})
    fireEvent.click(screen.getByRole('button',{name:'Review custom copy'}))
    expect(screen.getByText('before')).toBeInTheDocument()
    client.setQueryData(['world-package','real_world'],{...pkg,fingerprint:'after'})
    await waitFor(() => expect(screen.getByRole('button',{name:'Confirm custom copy'})).toBeDisabled())
    expect(api.cloneWorldPackage).not.toHaveBeenCalled()
  })




describe('custom World Package geography navigation', () => {
  it('guards the library link when Timezone Area edits are not yet reviewed', async () => {
    api.getWorldPackage.mockResolvedValue({
      world_id:'custom',name:'Custom world',description:'',type:'custom',source:'custom_config',
      status:'active',editable:true,deletable:true,archivable:true,version:'1',fingerprint:'fp',
      country_count:1,continent_count:0,region_count:0,travel_region_count:0,timezone_area_count:2,
      used_by_run_count:0,validation_status:'valid',
      storage:{package_root_path:'',world_metadata_path:'',countries_root_path:'',countries_index_path:'',
        geography_root_path:'',continents_path:'',regions_path:'',travel_regions_path:'',timezone_areas_path:''}
    })
    api.getWorldPackageGeography.mockResolvedValue({
      world_id:'custom',continents:[],regions:[],travel_regions:[],timezone_areas_authored:true,
      timezone_areas:[{code:'W',name:'West',position:0},{code:'E',name:'East',position:1}]
    })
    api.getWorldPackageValidation.mockResolvedValue({world_id:'custom',status:'valid',
      error_count:0,warning_count:0,info_count:0,checks:[]})
    const router = createMemoryRouter([
      {path:'/world/:worldId',element:<WorldLibraryDetailPage />},
      {path:'/admin/world/library',element:<p>Library opened</p>}
    ],{initialEntries:['/admin/world/library','/world/custom'],initialIndex:1})
    render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>
      <RouterProvider router={router} />
    </QueryClientProvider>)
    fireEvent.change(await screen.findByLabelText('Timezone Area name 0'),{target:{value:'Edited West'}})
    fireEvent.click(screen.getByRole('link',{name:'Back to World Library'}))
    expect(await screen.findByRole('alertdialog',{name:'Unsaved World Package changes'})).toBeInTheDocument()
    expect(screen.queryByText('Library opened')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Stay and keep editing'}))
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    // POP (browser Back) must be guarded just like an in-app Link.
    await act(async () => { await router.navigate(-1) })
    expect(await screen.findByRole('alertdialog',{name:'Unsaved World Package changes'})).toBeInTheDocument()
    expect(screen.queryByText('Library opened')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Stay and keep editing'}))
    fireEvent.click(screen.getByRole('link',{name:'Back to World Library'}))
    fireEvent.click(await screen.findByRole('button',{name:'Discard and leave'}))
    expect(await screen.findByText('Library opened')).toBeInTheDocument()
  })
})
