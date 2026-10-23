import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WorldLibraryDetailPage, WorldPackageCountryCreatePage } from './WorldLibraryPage'

const api = vi.hoisted(() => ({ getWorldPackage: vi.fn(), getWorldPackageGeography: vi.fn(), getWorldPackageValidation: vi.fn(), createWorldPackageCountry: vi.fn(), cloneWorldPackage: vi.fn() }))
const locale = vi.hoisted(() => ({ language: 'en' as 'cs' | 'en', listeners: new Set<() => void>() }))
vi.mock('../i18n/LanguageContext', async () => {
  const { useSyncExternalStore } = await import('react')
  return {
    useLanguage: () => ({
      language: useSyncExternalStore(
        (listener) => { locale.listeners.add(listener); return () => { locale.listeners.delete(listener) } },
        () => locale.language
      )
    })
  }
})
vi.mock('../api/client', async importOriginal => ({ ...(await importOriginal<object>()), ...api }))

beforeEach(() => { vi.clearAllMocks(); locale.language = 'en' })

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


it('explains duplicate Country code without mislabeling it as a package version conflict', async () => {
  api.getWorldPackage.mockResolvedValue({type:'custom',source:'custom_config',editable:true,
    fingerprint:'base-fp',world_id:'custom'})
  api.getWorldPackageGeography.mockResolvedValue({world_id:'custom',
    regions:[{code:'EUR',name:'Europe'}],travel_regions:[],timezone_areas:[]})
  api.createWorldPackageCountry.mockRejectedValue({status:409,message:"country 'AAA' already exists"})
  const router=createMemoryRouter([{path:'/world/:worldId/new',element:<WorldPackageCountryCreatePage />}],
    {initialEntries:['/world/custom/new']})
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}})}>
    <RouterProvider router={router} />
  </QueryClientProvider>)
  fireEvent.change(await screen.findByLabelText('Code'),{target:{value:'AAA'}})
  fireEvent.change(screen.getByLabelText('Name'),{target:{value:'Duplicate Country'}})
  fireEvent.change(screen.getByLabelText('Region'),{target:{value:'EUR'}})
  fireEvent.change(screen.getByLabelText('Population value 2020'),{target:{value:'100'}})
  fireEvent.click(screen.getByRole('button',{name:'Review before saving'}))
  fireEvent.click(screen.getByRole('button',{name:'Confirm and save'}))
  expect(await screen.findByText(/A country with this code already exists/)).toBeInTheDocument()
  expect(screen.queryByRole('button',{name:'Reload current data'})).not.toBeInTheDocument()
  expect(screen.getByRole('button',{name:'Confirm and save'})).toBeDisabled()
  expect(api.createWorldPackageCountry).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByRole('button',{name:'Back to editing'}))
  expect(screen.getByLabelText('Code')).toHaveValue('AAA')
})



describe('new Country conflict recovery and response identity', () => {
  function setupWithCustomWorld() {
    const source={type:'custom',source:'custom_config',editable:true,fingerprint:'create-base',world_id:'custom'}
    const geography={world_id:'custom',
      regions:[{code:'EUR',name:'Europe'}],travel_regions:[],timezone_areas:[]}
    api.getWorldPackage.mockResolvedValue(source)
    api.getWorldPackageGeography.mockResolvedValue(geography)
    const client=new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}})
    const router=createMemoryRouter([
      {path:'/world/:worldId/new',element:<WorldPackageCountryCreatePage />},
      {path:'*',element:<p>Other page</p>}
    ],{initialEntries:['/world/custom/new']})
    render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>)
    return {client,router,source,geography}
  }
  async function prepareNewCountry() {
    fireEvent.change(await screen.findByLabelText('Code'),{target:{value:'AAA'}})
    fireEvent.change(screen.getByLabelText('Name'),{target:{value:'Preserved Country'}})
    fireEvent.change(screen.getByLabelText('Region'),{target:{value:'EUR'}})
    fireEvent.change(screen.getByLabelText('Population value 2020'),{target:{value:'100'}})
    fireEvent.click(screen.getByRole('button',{name:'Review before saving'}))
    expect(await screen.findByText('Review new country')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Confirm and save'}))
  }

  it('preserves a reviewed new Country if a 409 reload fails, then clears it after a valid reload', async () => {
    const {source,geography}=setupWithCustomWorld()
    api.createWorldPackageCountry.mockRejectedValue({status:409,message:'world package changed'})
    await prepareNewCountry()
    expect(await screen.findByText(/No write was retried/)).toBeInTheDocument()
    const confirm=vi.spyOn(window,'confirm').mockReturnValue(true)
    api.getWorldPackage.mockRejectedValueOnce(new Error('Source offline'))
      .mockResolvedValue({...source,fingerprint:'fresh-fp'})
    fireEvent.click(screen.getByRole('button',{name:'Reload current data'}))
    expect(await screen.findByText(/Reload failed. Your draft Country has been preserved: Source offline/)).toBeInTheDocument()
    expect(screen.getByText('Preserved Country')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Confirm and save'})).toBeDisabled()
    expect(api.createWorldPackageCountry).toHaveBeenCalledTimes(1)
    api.getWorldPackageGeography.mockResolvedValue(geography)
    fireEvent.click(screen.getByRole('button',{name:'Reload current data'}))
    expect(await screen.findByLabelText('Code')).toHaveValue('')
    expect(screen.getByLabelText('Name')).toHaveValue('')
    expect(screen.getByLabelText('Population value 2020')).toHaveValue(null)
    expect(screen.queryByText('Review new country')).not.toBeInTheDocument()
    expect(screen.queryByText(/Reload failed/)).not.toBeInTheDocument()
    expect(confirm).toHaveBeenCalledTimes(2)
    expect(api.createWorldPackageCountry).toHaveBeenCalledTimes(1)
  })

  it('does not partially replace package cache if the companion geography reload fails', async () => {
    const {client,source,geography}=setupWithCustomWorld()
    api.createWorldPackageCountry.mockRejectedValue({status:409,message:'World Package changed'})
    await prepareNewCountry()
    expect(await screen.findByText(/No write was retried/)).toBeInTheDocument()
    vi.spyOn(window,'confirm').mockReturnValue(true)
    api.getWorldPackage.mockResolvedValue({...source,fingerprint:'premature-new-head'})
    api.getWorldPackageGeography.mockRejectedValueOnce(new Error('Geography temporarily unavailable'))
    fireEvent.click(screen.getByRole('button',{name:'Reload current data'}))
    expect(await screen.findByText(/Geography temporarily unavailable/)).toBeInTheDocument()
    expect(client.getQueryData<{fingerprint:string}>(['world-package','custom'])?.fingerprint).toBe('create-base')
    expect(screen.getByText('Preserved Country')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Confirm and save'})).toBeDisabled()
    api.getWorldPackageGeography.mockResolvedValue(geography)
    fireEvent.click(screen.getByRole('button',{name:'Reload current data'}))
    expect(await screen.findByLabelText('Code')).toHaveValue('')
    expect(client.getQueryData<{fingerprint:string}>(['world-package','custom'])?.fingerprint).toBe('premature-new-head')
    expect(api.createWorldPackageCountry).toHaveBeenCalledTimes(1)
  })

  it('rejects a mismatched create response rather than redirecting or claiming successful creation', async () => {
    const {router}=setupWithCustomWorld()
    api.createWorldPackageCountry.mockResolvedValue({
      country_detail:{package:{world_id:'other'},country:{code:'BBB'}},
      package:{world_id:'other'},validation:{status:'valid'}
    })
    await prepareNewCountry()
    expect(await screen.findByText(/server returned a different Country or World Package/i)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Confirm and save'})).toBeDisabled()
    expect(router.state.location.pathname).toBe('/world/custom/new')
    expect(screen.getByText('Preserved Country')).toBeInTheDocument()
    expect(api.createWorldPackageCountry).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button',{name:'Reload current data'})).toBeEnabled()
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
    api.cloneWorldPackage.mockImplementation(async (_worldId: string, payload: {dry_run:boolean}) => ({
      ok: true,
      dry_run: payload.dry_run,
      source_world_id: 'real_world',
      new_world_id: 'editable_earth',
      target_path: 'config/world_packages/custom/editable_earth',
      created_files: [],
      package: null,
      validation: null,
      errors: []
    }))

    const router = createMemoryRouter([
      {path:'/world/:worldId',element:<WorldLibraryDetailPage />},
      {path:'/admin/world/library/editable_earth',element:<p>Custom clone opened</p>}
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
    fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'Previewed description' } })
    fireEvent.click(screen.getByRole('button', { name: 'Preview clone' }))
    expect(await screen.findByText(/Preview only:/)).toBeInTheDocument()
    expect(api.cloneWorldPackage).toHaveBeenCalledWith('real_world', expect.objectContaining({dry_run:true}))
    fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'A personally edited description' } })
    expect(screen.queryByText(/Preview only:/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Review custom copy' }))
    expect(screen.getAllByText('real-world-head').length).toBeGreaterThan(0)
    expect(screen.getByText('A personally edited description')).toBeInTheDocument()
    expect(api.cloneWorldPackage).toHaveBeenCalledTimes(1)
    expect(api.cloneWorldPackage).not.toHaveBeenCalledWith('real_world', expect.objectContaining({dry_run:false}))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm custom copy' }))

    await waitFor(() => expect(api.cloneWorldPackage).toHaveBeenCalledWith(
      'real_world',
      expect.objectContaining({
        new_world_id: 'editable_earth', name: 'Editable Earth',
        description: 'A personally edited description', dry_run: false
      })
    ))
    fireEvent.click(await screen.findByRole('link', {name:'Open new Custom World detail'}))
    expect(await screen.findByText('Custom clone opened')).toBeInTheDocument()
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
  })

  it('translates preview, review and confirmed results without changing the requested clone', async () => {
    const source = {
      world_id: 'real_world', name: 'Real World', type: 'official', source: 'built_in',
      status: 'active', editable: false, fingerprint: 'original-fingerprint',
      country_count: 2, continent_count: 1, region_count: 1, travel_region_count: 1,
    }
    api.getWorldPackage.mockResolvedValue(source)
    api.getWorldPackageGeography.mockResolvedValue({
      world_id: 'real_world', continents: [], regions: [], travel_regions: [],
      timezone_areas: [], timezone_areas_authored: false,
    })
    api.getWorldPackageValidation.mockResolvedValue({
      world_id: 'real_world', status: 'valid', error_count: 0, warning_count: 0,
      info_count: 0, checks: [],
    })
    api.cloneWorldPackage.mockImplementation(async (worldId: string, payload: {dry_run: boolean}) => ({
      ok: true, dry_run: payload.dry_run,
      source_world_id: worldId, new_world_id: 'local_world',
      target_path: 'config/world_packages/custom/local_world',
      created_files: ['countries/AAA.json'],
      errors: [],
      package: {
        world_id: 'local_world', type: 'custom', source: 'custom_config',
        country_count: 2, continent_count: 1, region_count: 1, travel_region_count: 1,
        fingerprint: '0123456789abcdefghijklmnop',
      },
      validation: {status: 'valid', error_count: 0, warning_count: 1, info_count: 0},
    }))
    const client = new QueryClient({defaultOptions: {queries: {retry: false}}})
    const router = createMemoryRouter([{path: '/world/:worldId', element: <WorldLibraryDetailPage />}],
      {initialEntries: ['/world/real_world']})
    render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>)
    function switchLanguage(language: 'cs' | 'en') {
      act(() => {
        locale.language = language
        for (const listener of [...locale.listeners]) listener()
      })
    }

    expect(await screen.findByText('Clone Built-in World')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', {name: 'Review custom copy'}))
    expect(screen.getByText(/World ID must start with a lowercase letter or digit/)).toBeInTheDocument()
    switchLanguage('cs')
    expect(screen.getByText(/ID musí začínat malým písmenem nebo číslicí/)).toBeInTheDocument()
    expect(api.cloneWorldPackage).not.toHaveBeenCalled()
    switchLanguage('en')
    fireEvent.change(screen.getByPlaceholderText('my_custom_world'), {target: {value: 'local_world'}})
    fireEvent.change(screen.getByPlaceholderText('My Custom World'), {target: {value: 'Original authored name'}})
    fireEvent.click(screen.getByRole('button', {name: 'Review custom copy'}))
    expect(screen.getByText('Custom world cloned from Real World.')).toBeInTheDocument()
    switchLanguage('cs')
    expect(screen.getByRole('button', {name: 'Potvrdit vytvoření kopie'})).toBeInTheDocument()
    expect(screen.getByText('Custom world cloned from Real World.')).toBeInTheDocument()
    expect(screen.getAllByText('original-fingerprint').length).toBeGreaterThan(0)
    expect(api.cloneWorldPackage).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', {name: 'Zpět k formuláři'}))
    expect(screen.getByLabelText('Popis')).toHaveValue('Custom world cloned from Real World.')
    fireEvent.click(screen.getByRole('button', {name: 'Náhled kopírování'}))
    expect(await screen.findByText('Pouze náhled:')).toBeInTheDocument()
    expect(screen.getByText('Žádné soubory nebyly zapsány.')).toBeInTheDocument()
    expect(screen.getByText('Náhled balíčku')).toBeInTheDocument()
    expect(screen.getByText('Počty:')).toBeInTheDocument()
    expect(within(screen.getByLabelText('Výsledek kopírování')).getByText('Varování:')).toBeInTheDocument()
    expect(screen.getByText('countries/AAA.json')).toBeInTheDocument()
    expect(screen.getByText('config/world_packages/custom/local_world')).toBeInTheDocument()
    expect(screen.queryByRole('link', {name: /Otevřít detail nového/})).not.toBeInTheDocument()
    expect(api.cloneWorldPackage).toHaveBeenCalledWith('real_world', {
      new_world_id: 'local_world', name: 'Original authored name',
      description: 'Custom world cloned from Real World.', dry_run: true,
    })
    switchLanguage('en')
    expect(screen.getByText('Preview only:')).toBeInTheDocument()
    expect(screen.getByText('Package preview')).toBeInTheDocument()
    expect(within(screen.getByLabelText('Clone result')).getByText('Warnings:')).toBeInTheDocument()
    expect(api.cloneWorldPackage).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', {name: 'Review custom copy'}))
    expect(api.cloneWorldPackage).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', {name: 'Confirm custom copy'}))
    expect(await screen.findByText('Success:')).toBeInTheDocument()
    expect(screen.getByText('Created package')).toBeInTheDocument()
    expect(screen.getByRole('link', {name: 'Open new Custom World detail'}))
      .toHaveAttribute('href', '/admin/world/library/local_world')
    expect(api.cloneWorldPackage).toHaveBeenNthCalledWith(2, 'real_world', {
      new_world_id: 'local_world', name: 'Original authored name',
      description: 'Custom world cloned from Real World.', dry_run: false,
    })
    switchLanguage('cs')
    expect(screen.getByText('Úspěch:')).toBeInTheDocument()
    expect(screen.getByText('Vytvořený balíček')).toBeInTheDocument()
    expect(screen.getByRole('link', {name: 'Otevřít detail nového vlastního World Package'}))
      .toHaveAttribute('href', '/admin/world/library/local_world')
    expect(api.cloneWorldPackage).toHaveBeenCalledTimes(2)
  })

  it('translates a failed clone preview without rewriting server diagnostics or offering a created package', async () => {
    locale.language = 'cs'
    api.getWorldPackage.mockResolvedValue({
      world_id: 'real_world', name: 'Real World', type: 'official', source: 'built_in',
      status: 'active', editable: false, fingerprint: 'source-fingerprint',
      country_count: 1, continent_count: 1, region_count: 1, travel_region_count: 1,
    })
    api.getWorldPackageGeography.mockResolvedValue({
      world_id: 'real_world', continents: [], regions: [], travel_regions: [],
      timezone_areas: [], timezone_areas_authored: false,
    })
    api.getWorldPackageValidation.mockResolvedValue({
      world_id: 'real_world', status: 'valid', error_count: 0, warning_count: 0,
      info_count: 0, checks: [],
    })
    api.cloneWorldPackage.mockResolvedValue({
      ok: false, dry_run: true, source_world_id: 'real_world', new_world_id: 'local_world',
      target_path: 'config/world_packages/custom/local_world', created_files: [],
      package: null, validation: null,
      errors: [{field: 'new_world_id', message: 'DUPLICATE_WORLD_ID: preserved verbatim'}],
    })
    const router = createMemoryRouter([{path: '/world/:worldId', element: <WorldLibraryDetailPage />}],
      {initialEntries: ['/world/real_world']})
    render(<QueryClientProvider client={new QueryClient({defaultOptions: {queries: {retry: false}}})}>
      <RouterProvider router={router} />
    </QueryClientProvider>)
    fireEvent.change(await screen.findByPlaceholderText('my_custom_world'), {target: {value: 'local_world'}})
    fireEvent.change(screen.getByPlaceholderText('My Custom World'), {target: {value: 'Editable'}})
    fireEvent.click(screen.getByRole('button', {name: 'Náhled kopírování'}))
    expect(await screen.findByText('Náhled se nezdařil:')).toBeInTheDocument()
    expect(screen.getByText('Chyby kopírování:')).toBeInTheDocument()
    expect(screen.getByText('new_world_id: DUPLICATE_WORLD_ID: preserved verbatim')).toBeInTheDocument()
    expect(screen.queryByText('Úspěch:')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', {name: /Otevřít detail nového/})).not.toBeInTheDocument()
    expect(api.cloneWorldPackage).toHaveBeenCalledWith('real_world', expect.objectContaining({dry_run: true}))
  })

  it('keeps an in-flight preview and localizes a late mismatched response in the active language', async () => {
    api.getWorldPackage.mockResolvedValue({
      world_id: 'real_world', name: 'Original World', type: 'official', source: 'built_in',
      status: 'active', editable: false, fingerprint: 'immutable-source-fingerprint',
      country_count: 1, continent_count: 1, region_count: 1, travel_region_count: 1,
    })
    api.getWorldPackageGeography.mockResolvedValue({
      world_id: 'real_world', continents: [], regions: [], travel_regions: [],
      timezone_areas: [], timezone_areas_authored: false,
    })
    api.getWorldPackageValidation.mockResolvedValue({
      world_id: 'real_world', status: 'valid', error_count: 0, warning_count: 0,
      info_count: 0, checks: [],
    })
    let finish!: (response: unknown) => void
    api.cloneWorldPackage.mockImplementation(() => new Promise<unknown>(resolve => { finish = resolve }))
    const router = createMemoryRouter([{path: '/world/:worldId', element: <WorldLibraryDetailPage />}],
      {initialEntries: ['/world/real_world']})
    const client = new QueryClient({defaultOptions: {queries: {retry: false}}})
    render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>)
    const switchLanguage = (language: 'cs' | 'en') => act(() => {
      locale.language = language
      for (const listener of [...locale.listeners]) listener()
    })

    fireEvent.change(await screen.findByPlaceholderText('my_custom_world'), {target: {value: 'local_world'}})
    fireEvent.change(screen.getByPlaceholderText('My Custom World'), {target: {value: 'My authored name'}})
    fireEvent.click(screen.getByRole('button', {name: 'Preview clone'}))
    expect(api.cloneWorldPackage).toHaveBeenCalledWith('real_world', {
      new_world_id: 'local_world', name: 'My authored name',
      description: 'Custom world cloned from Original World.', dry_run: true,
    })
    switchLanguage('cs')
    expect(screen.getByLabelText('Popis')).toHaveValue('Custom world cloned from Original World.')
    expect(screen.getByRole('button', {name: 'Náhled kopírování'})).toBeDisabled()
    expect(api.cloneWorldPackage).toHaveBeenCalledTimes(1)

    await act(async () => finish({
      ok: true, dry_run: true, source_world_id: 'unrelated_world', new_world_id: 'local_world',
      target_path: 'config/world_packages/custom/local_world',
      created_files: [], package: null, validation: null, errors: [],
    }))
    expect(screen.getByRole('alert')).toHaveTextContent('Odpověď nepatří kontrolované kopii.')
    expect(screen.queryByText('Úspěch:')).not.toBeInTheDocument()
    switchLanguage('en')
    expect(screen.getByRole('alert')).toHaveTextContent('The response does not match the reviewed clone.')
    expect(api.cloneWorldPackage).toHaveBeenCalledTimes(1)
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
    expect(screen.getAllByText('before').length).toBeGreaterThan(0)
    client.setQueryData(['world-package','real_world'],{...pkg,fingerprint:'after'})
    await waitFor(() => expect(screen.getByRole('button',{name:'Confirm custom copy'})).toBeDisabled())
    expect(screen.getByText(/source World Package changed/i)).toBeInTheDocument()
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
