import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { TimezoneAreaEditor } from './TimezoneAreaEditor'
import type { WorldPackage, WorldPackageGeography } from '../../api/types'

const api = vi.hoisted(() => ({
  replaceWorldPackageTimezoneAreas: vi.fn(),
  getWorldPackage: vi.fn(),
  getWorldPackageGeography: vi.fn()
}))
vi.mock('../../api/client', async original => ({ ...(await original<object>()), ...api }))
vi.mock('../../i18n/LanguageContext', () => ({ useLanguage: () => ({ language: 'en' }) }))

function pkg(id = 'custom', editable = true, fingerprint = 'fp-1'): WorldPackage {
  return { world_id: id, name: id, description: null, type: editable ? 'custom' : 'official',
    source: editable ? 'custom_config' : 'built_in', status:'active', editable,
    deletable:editable,archivable:editable,version:'v1',fingerprint,
    country_count:2,continent_count:1,region_count:1,travel_region_count:1,
    timezone_area_count:2,used_by_run_count:0,validation_status:'valid' }
}
function geography(worldId = 'custom'): WorldPackageGeography {
  return {world_id: worldId,continents:[],regions:[],travel_regions:[],
    timezone_areas:[{code:'W',name:'West',position:0},{code:'E',name:'East',position:1}],
    timezone_areas_authored:true}
}
function setup(source = pkg(), regions = geography()) {
  const client = new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}})
  client.setQueryData(['world-package',source.world_id], source)
  const view = render(<QueryClientProvider client={client}>
    <TimezoneAreaEditor key={source.world_id} pkg={source} geography={regions} />
  </QueryClientProvider>)
  return {client, ...view}
}
beforeEach(() => {
  vi.clearAllMocks()
  api.getWorldPackage.mockImplementation(async (id: string) => pkg(id,true,'fp-2'))
  api.getWorldPackageGeography.mockImplementation(async (id: string) => geography(id))
})
afterEach(() => vi.restoreAllMocks())

describe('reviewed Timezone Area authoring', () => {
  it('requires review then submits exact ordered values and original fingerprint', async () => {
    const source = pkg()
    const {client} = setup(source)
    api.replaceWorldPackageTimezoneAreas.mockImplementation(async (worldId: string, areas: unknown[]) => {
      client.setQueryData(['world-package',worldId], pkg(worldId,true,'fp-after'))
      return {...geography(worldId),timezone_areas:areas}
    })
    fireEvent.click(screen.getAllByRole('button',{name:'Move Down'})[0])
    expect(screen.getByRole('button',{name:'Review Timezone Areas'})).toBeEnabled()
    fireEvent.click(screen.getByRole('button',{name:'Review Timezone Areas'}))
    expect(api.replaceWorldPackageTimezoneAreas).not.toHaveBeenCalled()
    expect(screen.getByText('fp-1')).toBeInTheDocument()
    expect(screen.getByText('W — West')).toBeInTheDocument()
    expect(screen.getByText('E — East')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Confirm and save'}))
    await waitFor(() => expect(api.replaceWorldPackageTimezoneAreas).toHaveBeenCalledWith('custom', [
      {code:'E',name:'East',position:0},{code:'W',name:'West',position:1}
    ],'fp-1'))
    expect(await screen.findByText(/Timezone Areas saved/)).toBeInTheDocument()
    expect(api.replaceWorldPackageTimezoneAreas).toHaveBeenCalledTimes(1)
  })

  it('rejects malformed codes, duplicates and empty rings locally', async () => {
    setup()
    fireEvent.change(screen.getByLabelText('Timezone Area code 1'),{target:{value:'W'}})
    fireEvent.click(screen.getByRole('button',{name:'Review Timezone Areas'}))
    expect(screen.getByText(/Duplicate Timezone Area code/)).toBeInTheDocument()
    expect(api.replaceWorldPackageTimezoneAreas).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText('Timezone Area code 1'),{target:{value:'lower'}})
    fireEvent.click(screen.getByRole('button',{name:'Review Timezone Areas'}))
    expect(screen.getByText(/must start with an uppercase/)).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button',{name:'Remove'})[0])
    fireEvent.click(screen.getAllByRole('button',{name:'Remove'})[0])
    fireEvent.click(screen.getByRole('button',{name:'Review Timezone Areas'}))
    expect(screen.getByText(/At least one Timezone Area/)).toBeInTheDocument()
  })

  it('does not retry on HTTP 409 and explicitly reloads current source', async () => {
    api.replaceWorldPackageTimezoneAreas.mockRejectedValue({status:409,message:'changed'})
    setup()
    fireEvent.change(screen.getByLabelText('Timezone Area name 1'),{target:{value:'East 2'}})
    fireEvent.click(screen.getByRole('button',{name:'Review Timezone Areas'}))
    fireEvent.click(screen.getByRole('button',{name:'Confirm and save'}))
    expect(await screen.findByText(/no write was retried/)).toBeInTheDocument()
    expect(api.replaceWorldPackageTimezoneAreas).toHaveBeenCalledTimes(1)
    const confirm = vi.spyOn(window,'confirm').mockReturnValue(true)
    fireEvent.click(screen.getByRole('button',{name:'Reload current data'}))
    await waitFor(() => expect(api.getWorldPackage).toHaveBeenCalledWith('custom'))
    await waitFor(() => expect(screen.getByLabelText('Timezone Area name 1')).toHaveValue('East'))
    expect(confirm).toHaveBeenCalled()
    expect(api.replaceWorldPackageTimezoneAreas).toHaveBeenCalledTimes(1)
  })

  it('blocks a confirmed preview after the package fingerprint changes', async () => {
    const source = pkg(), geo = geography()
    const {rerender,client} = setup(source,geo)
    fireEvent.change(screen.getByLabelText('Timezone Area name 0'),{target:{value:'New West'}})
    fireEvent.click(screen.getByRole('button',{name:'Review Timezone Areas'}))
    const latest = pkg('custom',true,'fp-other')
    client.setQueryData(['world-package','custom'],latest)
    rerender(<QueryClientProvider client={client}><TimezoneAreaEditor key="custom" pkg={latest} geography={geo} /></QueryClientProvider>)
    expect(screen.getByRole('button',{name:'Confirm and save'})).toBeDisabled()
    expect(api.replaceWorldPackageTimezoneAreas).not.toHaveBeenCalled()
    expect(screen.getByRole('button',{name:'Reload current data'})).toBeInTheDocument()
  })

  it('does not surface a delayed success in a different World Package', async () => {
    let finish!: (result: unknown) => void
    api.replaceWorldPackageTimezoneAreas.mockImplementation(() => new Promise(resolve => {finish=resolve}))
    const source=pkg(), firstGeo=geography()
    const {rerender,client} = setup(source,firstGeo)
    fireEvent.change(screen.getByLabelText('Timezone Area name 0'),{target:{value:'Changed West'}})
    fireEvent.click(screen.getByRole('button',{name:'Review Timezone Areas'}))
    fireEvent.click(screen.getByRole('button',{name:'Confirm and save'}))
    await waitFor(() => expect(api.replaceWorldPackageTimezoneAreas).toHaveBeenCalledWith('custom',expect.anything(),'fp-1'))
    const second = pkg('other')
    client.setQueryData(['world-package','other'],second)
    rerender(<QueryClientProvider client={client}>
      <TimezoneAreaEditor key="other" pkg={second} geography={geography('other')} />
    </QueryClientProvider>)
    await act(async () => { finish(geography('custom')) })
    expect(screen.queryByText(/Timezone Areas saved/)).not.toBeInTheDocument()
    expect(screen.getByLabelText('Timezone Area name 0')).toHaveValue('West')
    expect(api.replaceWorldPackageTimezoneAreas).toHaveBeenCalledTimes(1)
  })

  it('protects official and read-only World Packages', () => {
    setup(pkg('real_world',false),geography('real_world'))
    expect(screen.queryByLabelText('Timezone Area editor')).not.toBeInTheDocument()
    expect(api.replaceWorldPackageTimezoneAreas).not.toHaveBeenCalled()
  })
})
