import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderWithRoute } from '../test/testUtils'
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

describe('Run-owned World overview navigation',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    context.branch.run_id='run-a'
    context.time.mode='present'
    context.language='en'
    api.getRunPackageState.mockResolvedValue(worldFixture())
  })
  it('displays incomplete population, filters copied countries and links into six-tab detail preserving year/search',async()=>{
    renderWithRoute(<RunWorldPage/>,'/admin/runs/run-a/world?year=2000')
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
    renderWithRoute(<RunWorldPage/>,'/admin/runs/run-a/world/countries/CZE?year=2000&q=cze')
    expect(await screen.findByRole('heading',{name:/Czechia/})).toBeInTheDocument()
    expect(screen.getByRole('navigation',{name:'Country detail sections'}).querySelectorAll('a')).toHaveLength(6)
    expect(screen.getByText('EUROPE_CENTRAL')).toBeInTheDocument()
    expect(screen.getByRole('link',{name:/Back to countries/})).toHaveAttribute(
      'href','/admin/runs/run-a/world?year=2000&q=cze'
    )
    expect(api.getRunPackageState).toHaveBeenCalledTimes(1)
  })
  it('blocks present-only data at historical checkpoint without any current snapshot request',()=>{
    context.time.mode='checkpoint'
    renderWithRoute(<RunWorldPage/>,'/admin/runs/run-a/world')
    expect(screen.getByRole('alert')).toHaveTextContent('Historical checkpoint selected')
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })
  it('does not leak a foreign branch into World',()=>{
    context.branch.run_id='foreign'
    renderWithRoute(<RunWorldPage/>,'/admin/runs/run-a/world')
    expect(screen.getByRole('alert')).toHaveTextContent('Select a valid Branch')
    expect(api.getRunPackageState).not.toHaveBeenCalled()
  })
})
