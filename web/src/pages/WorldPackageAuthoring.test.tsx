import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { Link, RouterProvider, createMemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { WorldPackageCountryDetailPage } from './WorldLibraryPage'

const api = vi.hoisted(() => ({
  getWorldPackageCountry: vi.fn(),
  getWorldPackageGeography: vi.fn(),
  updateWorldPackageCountry: vi.fn(),
  updateWorldPackageCountryPopulation: vi.fn(),
  deleteWorldPackageCountry: vi.fn()
}))
vi.mock('../i18n/LanguageContext', () => ({ useLanguage: () => ({ language: 'en' }) }))
vi.mock('../api/client', async original => ({ ...(await original<object>()), ...api }))

function fixture(worldId = 'custom', code = 'AAA', editable = true) {
  return {
    package: { world_id: worldId, name: worldId, type: editable ? 'custom' : 'official',
      source: editable ? 'custom_config' : 'built_in', editable, fingerprint: `fingerprint-${worldId}` },
    country: { code, name: `Country ${code}`, notes: null, area_km2: 100, region: 'EUR',
      travel_region: null, timezone_area: null, squash_popularity: 5.5, squash_access: 5.5,
      development_quality: 5.5, competition_quality: 5.5, elite_support: 5.5,
      squash_tradition: 5.5, court_count: null, rating_scale: 'country_ratings_1_10.v2',
      population: 100, population_by_year: { '2020': 100 }, default_population: 100 },
    region: { code: 'EUR', name: 'Europe' }, travel_region: null,
    timezone_area: null, continent: null, source_path: 'custom'
  }
}
function setup(start = '/world/custom/countries/AAA') {
  const client = new QueryClient({defaultOptions: {queries: {retry: false}, mutations: {retry: false}}})
  const router = createMemoryRouter([{
    path:'/world/:worldId/countries/:countryCode',
    element:<><Link to="/world/other/countries/BBB">Switch country</Link><WorldPackageCountryDetailPage /></>
  },{path:'/admin/world/library',element:<p>Library opened</p>}],{initialEntries:[start]})
  return {router, client, ...render(<QueryClientProvider client={client}><RouterProvider router={router} /></QueryClientProvider>)}
}
beforeEach(() => {
  vi.clearAllMocks()
  api.getWorldPackageCountry.mockImplementation(async (worldId: string, code: string) => fixture(worldId, code))
  api.getWorldPackageGeography.mockImplementation(async (worldId: string) => ({
    world_id: worldId, regions:[{code:'EUR',name:'Europe'}], travel_regions:[], timezone_areas:[]
  }))
})
afterEach(() => vi.restoreAllMocks())

describe('World Package authoring against mutable source', () => {
  it('does not write without reviewing exact changes and fingerprint', async () => {
    api.updateWorldPackageCountry.mockImplementation(async () => ({country_detail: fixture(), validation: {status:'valid'}}))
    setup()
    fireEvent.click(await screen.findByRole('button', {name:'Edit country'}))
    fireEvent.change(screen.getByLabelText('Name'), {target:{value:'Renamed country'}})
    fireEvent.click(screen.getByRole('button', {name:'Review changes'}))
    expect(api.updateWorldPackageCountry).not.toHaveBeenCalled()
    expect(screen.getByText('Review country changes')).toBeInTheDocument()
    expect(screen.getByText('fingerprint-custom')).toBeInTheDocument()
    expect(screen.getByText('Renamed country')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', {name:'Confirm and save'}))
    await waitFor(() => expect(api.updateWorldPackageCountry).toHaveBeenCalledWith(
      'custom', 'AAA', expect.objectContaining({
        expected_package_fingerprint:'fingerprint-custom',name:'Renamed country'
      })
    ))
  })

  it('reports a 409, never retries automatically and offers explicit reload', async () => {
    api.updateWorldPackageCountry.mockRejectedValue({status:409,message:'World Package changed'})
    setup()
    fireEvent.click(await screen.findByRole('button', {name:'Edit country'}))
    fireEvent.change(screen.getByLabelText('Name'), {target:{value:'Reviewed name'}})
    fireEvent.click(screen.getByRole('button', {name:'Review changes'}))
    fireEvent.click(screen.getByRole('button', {name:'Confirm and save'}))
    expect(await screen.findByText(/No write was retried/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Confirm and save'})).toBeDisabled()
    expect(api.updateWorldPackageCountry).toHaveBeenCalledTimes(1)
    const confirm = vi.spyOn(window,'confirm').mockReturnValue(true)
    fireEvent.click(screen.getByRole('button', {name:'Reload current data'}))
    await waitFor(() => expect(api.getWorldPackageCountry).toHaveBeenCalledTimes(2))
    expect(confirm).toHaveBeenCalled()
    expect(api.updateWorldPackageCountry).toHaveBeenCalledTimes(1)
  })

  it('keeps a conflicted Country draft intact if the approved reload fails', async () => {
    api.updateWorldPackageCountry.mockRejectedValue({status:409,message:'World Package changed'})
    api.getWorldPackageCountry.mockImplementationOnce(async () => fixture())
      .mockRejectedValueOnce(new Error('Network offline'))
      .mockImplementation(async () => ({...fixture(),package:{...fixture().package,fingerprint:'fresh-head'}}))
    setup()
    fireEvent.click(await screen.findByRole('button',{name:'Edit country'}))
    fireEvent.change(screen.getByLabelText('Name'),{target:{value:'Unsaved Reviewed Name'}})
    fireEvent.click(screen.getByRole('button',{name:'Review changes'}))
    fireEvent.click(screen.getByRole('button',{name:'Confirm and save'}))
    expect(await screen.findByText(/No write was retried/)).toBeInTheDocument()
    vi.spyOn(window,'confirm').mockReturnValue(true)
    fireEvent.click(screen.getByRole('button',{name:'Reload current data'}))
    expect(await screen.findByText(/Reload failed. Your existing draft has been preserved: Network offline/)).toBeInTheDocument()
    expect(screen.getByText('Unsaved Reviewed Name')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Confirm and save'})).toBeDisabled()
    expect(api.updateWorldPackageCountry).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button',{name:'Reload current data'}))
    await waitFor(() => expect(screen.queryByRole('heading',{name:'Review country changes'})).not.toBeInTheDocument())
    expect(screen.queryByText(/Reload failed/)).not.toBeInTheDocument()
    expect(api.updateWorldPackageCountry).toHaveBeenCalledTimes(1)
  })

  it('rejects a wrong-country update response without poisoning the original Country cache', async () => {
    api.updateWorldPackageCountry.mockResolvedValue({
      country_detail:fixture('other','BBB'),
      validation:{status:'valid'}
    })
    const {client} = setup()
    fireEvent.click(await screen.findByRole('button',{name:'Edit country'}))
    fireEvent.change(screen.getByLabelText('Name'),{target:{value:'Reviewed Name'}})
    fireEvent.click(screen.getByRole('button',{name:'Review changes'}))
    fireEvent.click(screen.getByRole('button',{name:'Confirm and save'}))
    expect(await screen.findByText(/server returned a different Country or World Package/i)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Confirm and save'})).toBeDisabled()
    expect(screen.queryByText(/Country saved/)).not.toBeInTheDocument()
    expect(client.getQueryData<{country:{code:string}}>(['world-package-country','custom','AAA'])?.country.code).toBe('AAA')
    expect(api.updateWorldPackageCountry).toHaveBeenCalledTimes(1)
  })

  it('rejects a wrong-package population update response and keeps reviewed population changes', async () => {
    api.updateWorldPackageCountryPopulation.mockResolvedValue({
      country_detail:fixture('other','AAA'),
      validation:{status:'valid'}
    })
    setup()
    fireEvent.click(await screen.findByRole('button',{name:'Edit population'}))
    fireEvent.change(screen.getByLabelText('Population 2020'),{target:{value:'150'}})
    fireEvent.click(screen.getByRole('button',{name:'Review changes'}))
    fireEvent.click(screen.getByRole('button',{name:'Confirm and save'}))
    expect(await screen.findByText(/server returned a different Country or World Package/i)).toBeInTheDocument()
    expect(screen.getByText('150')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Confirm and save'})).toBeDisabled()
    expect(screen.queryByText(/Population saved/)).not.toBeInTheDocument()
    expect(api.updateWorldPackageCountryPopulation).toHaveBeenCalledTimes(1)
  })

  it('does not route a paused country write to a newly selected package', async () => {
    let finish!: (value: unknown) => void
    api.updateWorldPackageCountry.mockImplementation(() => new Promise(resolve => {finish = resolve}))
    setup()
    fireEvent.click(await screen.findByRole('button', {name:'Edit country'}))
    fireEvent.change(screen.getByLabelText('Name'), {target:{value:'Old pending edit'}})
    fireEvent.click(screen.getByRole('button', {name:'Review changes'}))
    fireEvent.click(screen.getByRole('button', {name:'Confirm and save'}))
    await waitFor(() => expect(api.updateWorldPackageCountry).toHaveBeenCalledWith('custom','AAA',expect.anything()))
    fireEvent.click(screen.getByRole('link', {name:'Switch country'}))
    expect(await screen.findByRole('alertdialog',{name:'Unsaved World Package changes'})).toBeInTheDocument()
    expect(screen.queryByRole('heading',{name:'Country BBB'})).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Discard and leave'}))
    expect(await screen.findByRole('heading', {name:'Country BBB'})).toBeInTheDocument()
    finish({country_detail:fixture(),validation:{status:'valid'}})
    await waitFor(() => expect(api.getWorldPackageCountry).toHaveBeenCalledWith('other','BBB'))
    expect(screen.queryByText(/Country saved/)).not.toBeInTheDocument()
    expect(api.updateWorldPackageCountry).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('heading', {name:'Country BBB'})).toBeInTheDocument()
  })

  it('never offers editing or deletion on a protected built-in source', async () => {
    api.getWorldPackageCountry.mockResolvedValue(fixture('official','FAX',false))
    setup('/world/official/countries/FAX')
    expect(await screen.findByRole('heading', {name:'Country FAX'})).toBeInTheDocument()
    expect(screen.queryByRole('button', {name:'Edit country'})).not.toBeInTheDocument()
    expect(screen.queryByRole('button', {name:'Edit population'})).not.toBeInTheDocument()
    expect(screen.queryByRole('button', {name:'Delete country'})).not.toBeInTheDocument()
  })

  it('reviews precise population changes with no write before confirmation', async () => {
    api.updateWorldPackageCountryPopulation.mockResolvedValue({country_detail:fixture(),validation:{status:'valid'}})
    setup()
    fireEvent.click(await screen.findByRole('button', {name:'Edit population'}))
    fireEvent.change(screen.getByLabelText('Population 2020'), {target:{value:'120'}})
    fireEvent.click(screen.getByRole('button', {name:'Review changes'}))
    expect(api.updateWorldPackageCountryPopulation).not.toHaveBeenCalled()
    expect(screen.getByText('120')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', {name:'Confirm and save'}))
    await waitFor(() => expect(api.updateWorldPackageCountryPopulation).toHaveBeenCalledWith(
      'custom','AAA',{values_by_year:{'2020':120},expected_package_fingerprint:'fingerprint-custom'}
    ))
  })
  it('does not redirect after deletion completes on a page the user already left', async () => {
    let finish!: (response: unknown) => void
    api.deleteWorldPackageCountry.mockImplementation(() => new Promise(resolve => { finish = resolve }))
    const {router} = setup()
    fireEvent.click(await screen.findByRole('button',{name:'Delete country'}))
    vi.spyOn(window,'confirm').mockReturnValue(true)
    fireEvent.click(screen.getByRole('button',{name:'Confirm deletion'}))
    await waitFor(() => expect(api.deleteWorldPackageCountry).toHaveBeenCalledWith('custom','AAA','fingerprint-custom'))
    fireEvent.click(screen.getByRole('link',{name:'World Packages'}))
    expect(await screen.findByText('Library opened')).toBeInTheDocument()
    await act(async () => { finish({deleted_country_code:'AAA',package:{world_id:'custom'},validation:{status:'valid'}}) })
    expect(router.state.location.pathname).toBe('/admin/world/library')
    expect(screen.getByText('Library opened')).toBeInTheDocument()
  })

  it('does not navigate or claim deletion when the response names a different Country', async () => {
    api.deleteWorldPackageCountry.mockResolvedValue({
      deleted_country_code:'ZZZ',package:{world_id:'custom'},validation:{status:'valid'}
    })
    const {router} = setup()
    fireEvent.click(await screen.findByRole('button',{name:'Delete country'}))
    vi.spyOn(window,'confirm').mockReturnValue(true)
    fireEvent.click(screen.getByRole('button',{name:'Confirm deletion'}))
    expect(await screen.findByText(/server returned a different Country or World Package/i)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Confirm deletion'})).toBeDisabled()
    expect(router.state.location.pathname).toBe('/world/custom/countries/AAA')
    expect(api.deleteWorldPackageCountry).toHaveBeenCalledTimes(1)
  })

  it('freezes delete fingerprint and rejects a changed package before destructive confirmation', async () => {
    const {client} = setup()
    fireEvent.click(await screen.findByRole('button',{name:'Delete country'}))
    expect(screen.getByText('fingerprint-custom')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Confirm deletion'})).toBeEnabled()
    const changed = fixture()
    changed.package.fingerprint = 'new-fingerprint'
    client.setQueryData(['world-package-country','custom','AAA'],changed)
    expect(await screen.findByText(/Deletion is blocked/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Confirm deletion'})).toBeDisabled()
    expect(screen.getByText('fingerprint-custom')).toBeInTheDocument()
    expect(api.deleteWorldPackageCountry).not.toHaveBeenCalled()
  })

})
